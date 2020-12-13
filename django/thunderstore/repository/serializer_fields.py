from django.core.validators import RegexValidator
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from thunderstore.repository.consts import PACKAGE_NAME_REGEX, PACKAGE_VERSION_REGEX
from thunderstore.repository.models import PackageVersion, UploaderIdentity
from thunderstore.repository.package_reference import PackageReference
from thunderstore.repository.validators import (
    AuthorNameRegexValidator,
    PackageReferenceValidator,
    VersionNumberValidator,
    license_validator,
)


class DependencyField(serializers.Field):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.validators.append(
            PackageReferenceValidator(require_version=True, resolve=True)
        )

    def to_internal_value(self, data):
        try:
            return PackageReference.parse(str(data))
        except ValueError as exc:
            raise ValidationError(str(exc))

    def to_representation(self, value):
        return str(value)


class PackageNameField(serializers.CharField):
    def __init__(self, **kwargs):
        kwargs["max_length"] = PackageVersion._meta.get_field("name").max_length
        kwargs["allow_blank"] = False
        super().__init__(**kwargs)
        validator = RegexValidator(
            PACKAGE_NAME_REGEX,
            message=f"Package names can only contain a-Z A-Z 0-9 _ characers",
        )
        self.validators.append(validator)


class PackageAuthorNameField(serializers.CharField):
    def __init__(self, **kwargs):
        kwargs["max_length"] = UploaderIdentity._meta.get_field("name").max_length
        kwargs["allow_blank"] = False
        super().__init__(**kwargs)
        validator = AuthorNameRegexValidator
        self.validators.append(validator)


class PackageVersionField(serializers.CharField):
    def __init__(self, **kwargs):
        kwargs["max_length"] = PackageVersion._meta.get_field(
            "version_number"
        ).max_length
        kwargs["allow_blank"] = False
        super().__init__(**kwargs)
        regex_validator = RegexValidator(
            PACKAGE_VERSION_REGEX,
            message=f"Version numbers must follow the Major.Minor.Patch format (e.g. 1.45.320)",
        )
        version_number_validator = VersionNumberValidator()
        self.validators.append(regex_validator)
        self.validators.append(version_number_validator)


# Can be more optimised than ChoiceField as the list of licenses is a set
# Not part of the model as IDs may be deprecated
class LicenseField(serializers.CharField):
    def __init__(self, **kwargs):
        kwargs["allow_blank"] = True
        super().__init__(**kwargs)
        self.validators.append(license_validator)
