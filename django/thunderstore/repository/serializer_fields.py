from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import RegexValidator
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from thunderstore.repository.consts import PACKAGE_NAME_REGEX, PACKAGE_VERSION_REGEX
from thunderstore.repository.models import PackageVersion
from thunderstore.repository.package_reference import PackageReference
from thunderstore.repository.validators import (
    PackageReferenceValidator,
    VersionNumberValidator,
)


class ModelChoiceField(serializers.Field):
    default_error_messages = {
        "not_found": _("Object not found"),
    }
    initial = ""

    def __init__(self, queryset: QuerySet, to_field: str, **kwargs):
        self.queryset = queryset
        self.to_field = to_field
        super().__init__(**kwargs)

    def get_queryset(self):
        return self.queryset

    def to_internal_value(self, data):
        try:
            return self.get_queryset().get(**{self.to_field: data})
        except ObjectDoesNotExist:
            self.fail("not_found")

    def to_representation(self, value):
        return str(getattr(value, self.to_field))


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
