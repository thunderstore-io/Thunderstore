from typing import Optional
from zipfile import BadZipFile, ZipFile

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction

from thunderstore.community.models import Community, PackageCategory
from thunderstore.core.types import UserType
from thunderstore.repository.models import Package, PackageVersion, Team
from thunderstore.repository.package_formats import PackageFormats
from thunderstore.repository.validation.icon import validate_icon
from thunderstore.repository.validation.manifest import validate_manifest
from thunderstore.repository.validation.readme import validate_readme

MAX_PACKAGE_SIZE = 1024 * 1024 * settings.REPOSITORY_MAX_PACKAGE_SIZE_MB
MIN_PACKAGE_SIZE = 1  # Honestly impossible, but need to set some value
MAX_TOTAL_SIZE = 1024 * 1024 * 1024 * settings.REPOSITORY_MAX_PACKAGE_TOTAL_SIZE_GB


class PackageUploadForm(forms.ModelForm):
    # TODO: Convert the package validation process to a more functionally
    #       pure solution to reduce the probability of validation bugs when
    #       multiple formats are supported simultaneously.
    # TODO: Utilize the format spec in the entirety of the validation pipeline
    #       and make it impossible to avoid doing so (in code).
    format_spec = PackageFormats.v0_1
    categories = forms.ModelMultipleChoiceField(
        queryset=PackageCategory.objects.none(),
        required=False,
    )
    team = forms.ModelChoiceField(
        queryset=Team.objects.none(),
        to_field_name="name",
        required=True,
        empty_label=None,
    )
    communities = forms.ModelMultipleChoiceField(
        queryset=Community.objects.all(),
        to_field_name="identifier",
        required=True,
    )
    has_nsfw_content = forms.BooleanField(required=False)

    class Meta:
        model = PackageVersion
        fields = ["team", "file"]

    def __init__(
        self,
        user: UserType,
        community: Community,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.user = user
        self.community = community
        # TODO: How to handle with multi-community? Let's just default to the
        #       currently active community for the sake of simplicity
        self.fields["categories"].queryset = PackageCategory.objects.filter(
            community=community
        )
        # TODO: Query only teams where the user has upload permission
        self.fields["team"].queryset = Team.objects.filter(
            members__user=self.user,
        )
        # TODO: Move this to the frontent code somehow
        self.fields["team"].widget.attrs["class"] = "slimselect-lg"
        self.manifest: Optional[dict] = None
        self.icon: Optional[ContentFile] = None
        self.readme: Optional[str] = None
        self.file_size: Optional[int] = None

    def validate_manifest(self, manifest: bytes):
        self.manifest = validate_manifest(
            format_spec=self.format_spec,
            user=self.user,
            team=self.cleaned_data.get("team"),
            manifest_data=manifest,
        )

    def validate_icon(self, icon: bytes):
        self.icon = validate_icon(icon)

    def validate_readme(self, readme: bytes):
        try:
            self.readme = validate_readme(readme)
        except ValidationError as e:
            self.add_error(None, e)

    def clean_file(self):
        file = self.cleaned_data.get("file", None)
        if not file:
            raise ValidationError("Must upload a file")

        if file.size > MAX_PACKAGE_SIZE:
            raise ValidationError(
                f"Too large package, current maximum is {MAX_PACKAGE_SIZE} bytes"
            )
        self.file_size = file.size

        if file.size + PackageVersion.get_total_used_disk_space() > MAX_TOTAL_SIZE:
            raise ValidationError(
                f"The server has reached maximum total storage used, and can't receive new uploads"
            )

        try:
            with ZipFile(file) as unzip:

                if unzip.testzip():
                    raise ValidationError("Corrupted zip file")

                try:
                    manifest = unzip.read("manifest.json")
                    self.validate_manifest(manifest)
                except KeyError:
                    raise ValidationError("Package is missing manifest.json")

                try:
                    icon = unzip.read("icon.png")
                    self.validate_icon(icon)
                except KeyError:
                    raise ValidationError("Package is missing icon.png")

                try:
                    readme = unzip.read("README.md")
                    self.validate_readme(readme)
                except KeyError:
                    raise ValidationError("Package is missing README.md")

        except (BadZipFile, NotImplementedError):
            raise ValidationError("Invalid zip file format")

        return file

    def clean_team(self):
        team = self.cleaned_data["team"]
        team.ensure_can_upload_package(self.user)
        return team

    @transaction.atomic
    def save(self, *args, **kwargs):
        self.instance.name = self.manifest["name"]
        self.instance.version_number = self.manifest["version_number"]
        self.instance.website_url = self.manifest["website_url"]
        self.instance.description = self.manifest["description"]
        self.instance.readme = self.readme
        self.instance.file_size = self.file_size
        self.instance.format_spec = self.format_spec
        team = self.cleaned_data["team"]
        team.ensure_can_upload_package(self.user)
        # We just take the namespace with team name for now
        namespace = team.get_namespace()
        self.instance.package = Package.objects.get_or_create(
            owner=team, name=self.instance.name, namespace=namespace
        )[0]

        for community in self.cleaned_data.get("communities", []):
            categories = []
            if community == self.community:
                categories = self.cleaned_data.get("categories", [])
            self.instance.package.update_listing(
                has_nsfw_content=self.cleaned_data.get("has_nsfw_content", False),
                categories=categories,
                community=community,
            )

        self.instance.icon.save("icon.png", self.icon)
        instance = super().save()
        for reference in self.manifest["dependencies"]:
            instance.dependencies.add(reference.instance)
        return instance
