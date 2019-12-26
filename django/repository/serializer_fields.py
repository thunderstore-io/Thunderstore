from django.core.validators import RegexValidator
from rest_framework import serializers

from repository.consts import PACKAGE_NAME_REGEX, PACKAGE_VERSION_REGEX
from repository.models import PackageVersion
from repository.validators import VersionNumberValidator


class PackageNameField(serializers.CharField):
    def __init__(self, **kwargs):
        kwargs["max_length"] = PackageVersion._meta.get_field("name").max_length
        kwargs["allow_blank"] = False
        super().__init__(**kwargs)
        validator = RegexValidator(
            PACKAGE_NAME_REGEX,
            message=f"Package names can only contain a-Z A-Z 0-9 _ characers"
        )
        self.validators.append(validator)


class PackageVersionField(serializers.CharField):
    def __init__(self, **kwargs):
        kwargs["max_length"] = PackageVersion._meta.get_field("version_number").max_length
        kwargs["allow_blank"] = False
        super().__init__(**kwargs)
        regex_validator = RegexValidator(
            PACKAGE_VERSION_REGEX,
            message=f"Version numbers must follow the Major.Minor.Patch format (e.g. 1.45.320)"
        )
        version_number_validator = VersionNumberValidator()
        self.validators.append(regex_validator)
        self.validators.append(version_number_validator)
