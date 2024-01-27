from django.core.validators import URLValidator
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from thunderstore.repository.models import PackageVersion
from thunderstore.repository.package_reference import PackageReference
from thunderstore.repository.serializer_fields import (
    DependencyField,
    PackageNameField,
    PackageNamespaceField,
    PackageVersionField,
    StrictCharField,
)
from thunderstore.repository.utils import does_contain_package, has_duplicate_packages


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
    namespace = PackageNamespaceField(required=False)
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
        return result

    def update(self, instance, validated_data):
        raise NotImplementedError(".update() is not supported")

    def create(self, validated_data):
        raise NotImplementedError(".create() is not supported")
