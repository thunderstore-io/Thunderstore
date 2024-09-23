from typing import List, TypedDict

from django.core.validators import URLValidator
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from thunderstore.repository.models import PackageInstaller, PackageVersion
from thunderstore.repository.package_reference import PackageReference
from thunderstore.repository.serializer_fields import (
    DependencyField,
    ModelChoiceField,
    PackageNameField,
    PackageVersionField,
    StrictCharField,
)
from thunderstore.repository.utils import (
    does_contain_package,
    has_different_case,
    has_duplicate_packages,
)


class PackageInstallerSerializer(serializers.Serializer):
    identifier = ModelChoiceField(
        queryset=PackageInstaller.objects.all(),
        required=True,
        to_field="identifier",
        error_messages={"not_found": "Matching installer not found."},
    )
    # Potential to expand this in the future with installer-specific arguments.
    # Not yet added as to not create backwards incompatibilities if the field
    # ends up unused.

    class Type(TypedDict):
        identifier: PackageInstaller


def validate_unique_installers(installers: List[PackageInstallerSerializer.Type]):
    seen = set()
    for entry in [x["identifier"].identifier for x in installers]:
        if entry in seen:
            raise ValidationError(f"Duplicate use of installer {entry}")
        seen.add(entry)


class ManifestV1Serializer(serializers.Serializer):
    def __init__(self, *args, **kwargs):
        if "user" not in kwargs:
            raise AttributeError("Missing required key word parameter: user")
        if "team" not in kwargs:
            raise AttributeError("Missing required key word parameter: team")
        self.user = kwargs.pop("user")
        self.team = kwargs.pop("team")
        super().__init__(*args, **kwargs)

    name = PackageNameField()
    version_number = PackageVersionField()
    website_url = StrictCharField(
        max_length=PackageVersion._meta.get_field("website_url").max_length,
        allow_blank=True,
        validators=[URLValidator(schemes=["http", "https", "mailto", "ipfs"])],
    )
    description = StrictCharField(
        max_length=PackageVersion._meta.get_field("description").max_length,
        allow_blank=True,
    )
    dependencies = serializers.ListField(
        child=DependencyField(),
        max_length=1000,
        allow_empty=True,
    )
    installers = serializers.ListField(
        child=PackageInstallerSerializer(),
        validators=[validate_unique_installers],
        max_length=100,
        min_length=1,
        allow_empty=False,
        allow_null=False,
        required=False,
    )

    def validate(self, data):
        result = super().validate(data)
        if self.team is None:
            raise ValidationError("Unable to validate package when no team is selected")
        if not self.team.can_user_upload(self.user):
            raise ValidationError(
                f"Missing privileges to upload under author {self.team.name}"
            )
        reference = PackageReference(
            self.team.name, result["name"], result["version_number"]
        )
        if reference.exists:
            raise ValidationError(
                "Package of the same namespace, name and version already exists"
            )
        if has_duplicate_packages(result["dependencies"]):
            raise ValidationError(
                "Cannot depend on multiple versions of the same package"
            )
        if does_contain_package(result["dependencies"], reference):
            raise ValidationError("Package depending on itself is not allowed")
        if has_different_case(reference.without_version):
            raise ValidationError(
                "Package name already exists with different capitalization"
            )
        return result

    def update(self, instance, validated_data):
        raise NotImplementedError(".update() is not supported")

    def create(self, validated_data):
        raise NotImplementedError(".create() is not supported")
