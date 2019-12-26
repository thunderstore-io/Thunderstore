from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from repository.models import PackageVersion
from repository.package_reference import PackageReference
from repository.serializer_fields import DependencyField
from repository.serializer_fields import PackageVersionField
from repository.serializer_fields import PackageNameField
from repository.utils import does_contain_package, has_duplicate_packages


class ManifestV1Serializer(serializers.Serializer):

    def __init__(self, *args, **kwargs):
        if "user" not in kwargs:
            raise AttributeError("Missing required key word parameter: user")
        if "uploader" not in kwargs:
            raise AttributeError("Missing required key word parameter: uploader")
        self.user = kwargs.pop("user")
        self.uploader = kwargs.pop("uploader")
        super().__init__(*args, **kwargs)

    name = PackageNameField()
    version_number = PackageVersionField()
    website_url = serializers.CharField(
        max_length=PackageVersion._meta.get_field("website_url").max_length,
        allow_blank=True,
    )
    description = serializers.CharField(
        max_length=PackageVersion._meta.get_field("description").max_length,
        allow_blank=True,
    )
    dependencies = serializers.ListField(
        child=DependencyField(),
        max_length=100,
        allow_empty=True,
    )

    def validate(self, data):
        result = super().validate(data)
        if not self.uploader.can_user_upload(self.user):
            raise ValidationError(f"Missing privileges to upload under author {self.uploader.name}")
        reference = PackageReference(self.uploader.name, result["name"], result["version_number"])
        if reference.exists:
            raise ValidationError("Package of the same name and version already exists")
        if has_duplicate_packages(result["dependencies"]):
            raise ValidationError("Cannot depend on multiple versions of the same package")
        if does_contain_package(result["dependencies"], reference):
            raise ValidationError("Package depending on itself is not allowed")
        return result

    def update(self, instance, validated_data):
        raise NotImplementedError(".update() is not supported")

    def create(self, validated_data):
        raise NotImplementedError(".create() is not supported")
