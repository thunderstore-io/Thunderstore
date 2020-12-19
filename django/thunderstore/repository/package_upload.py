import io
import json
from typing import Optional
from zipfile import BadZipFile, ZipFile

from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image

from thunderstore.community.models import Community, PackageCategory
from thunderstore.repository.models import Package, PackageVersion, UploaderIdentity
from thunderstore.repository.package_manifest import ManifestV1Serializer

MAX_PACKAGE_SIZE = 1024 * 1024 * 500
MAX_ICON_SIZE = 1024 * 1024 * 6
MAX_TOTAL_SIZE = 1024 * 1024 * 1024 * 500


def unpack_serializer_errors(field, errors, error_dict=None):
    if error_dict is None:
        error_dict = {}

    if isinstance(errors, list) and len(errors) == 1:
        errors = errors[0]

    if isinstance(errors, dict):
        for key, value in errors.items():
            error_dict = unpack_serializer_errors(f"{field} {key}", value, error_dict)
    elif isinstance(errors, list):
        for index, entry in enumerate(errors):
            error_dict = unpack_serializer_errors(f"{field} {index}", entry, error_dict)
    else:
        error_dict[field] = str(errors)
    return error_dict


class PackageUploadForm(forms.ModelForm):
    categories = forms.ModelMultipleChoiceField(
        queryset=PackageCategory.objects.none(), required=False
    )
    has_nsfw_content = forms.BooleanField(required=False)

    class Meta:
        model = PackageVersion
        fields = ["file"]

    def __init__(self, user, identity, community, *args, **kwargs):
        super(PackageUploadForm, self).__init__(*args, **kwargs)
        self.user: User = user
        self.identity: UploaderIdentity = identity
        self.community: Community = community
        self.fields["categories"].queryset = PackageCategory.objects.filter(
            community=community
        )
        self.manifest: Optional[dict] = None
        self.icon: Optional[ContentFile] = None
        self.readme: Optional[str] = None
        self.file_size: Optional[int] = None

    def validate_manifest(self, manifest_str):
        try:
            manifest_data = json.loads(manifest_str)
        except json.decoder.JSONDecodeError as exc:
            raise ValidationError(f"Unable to parse manifest.json: {exc}")

        serializer = ManifestV1Serializer(
            user=self.user,
            uploader=self.identity,
            data=manifest_data,
        )
        if serializer.is_valid():
            self.manifest = serializer.validated_data
        else:
            errors = unpack_serializer_errors("manifest.json", serializer.errors)
            errors = ValidationError(
                [f"{key}: {value}" for key, value in errors.items()]
            )
            self.add_error(None, errors)

    def validate_icon(self, icon):
        try:
            self.icon = ContentFile(icon)
        except Exception:
            raise ValidationError("Unknown error while processing icon.png")

        if self.icon.size > MAX_ICON_SIZE:
            raise ValidationError(
                f"icon.png filesize is too big, current maximum is {MAX_ICON_SIZE} bytes"
            )

        try:
            image = Image.open(io.BytesIO(icon))
        except Exception:
            raise ValidationError("Unsupported or corrupt icon, must be png")

        if image.format != "PNG":
            raise ValidationError("Icon must be in png format")

        if not (image.size[0] == 256 and image.size[1] == 256):
            raise ValidationError("Invalid icon dimensions, must be 256x256")

    def validate_readme(self, readme):
        readme = readme.decode("utf-8")
        max_length = 32768
        if len(readme) > max_length:
            raise ValidationError(f"README.md is too long, max: {max_length}")
        self.readme = readme

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

    def save(self, *args, **kwargs):
        self.instance.name = self.manifest["name"]
        self.instance.version_number = self.manifest["version_number"]
        self.instance.website_url = self.manifest["website_url"]
        self.instance.description = self.manifest["description"]
        self.instance.readme = self.readme
        self.instance.file_size = self.file_size
        self.instance.package = Package.objects.get_or_create(
            owner=self.identity,
            name=self.instance.name,
        )[0]
        self.instance.package.update_listing(
            has_nsfw_content=self.cleaned_data.get("has_nsfw_content", False),
            categories=self.cleaned_data.get("categories", []),
            community=self.community,
        )
        self.instance.icon.save("icon.png", self.icon)
        instance = super().save()
        for reference in self.manifest["dependencies"]:
            instance.dependencies.add(reference.instance)
        return instance
