from distutils.version import StrictVersion

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.deconstruct import deconstructible

from thunderstore.repository.consts import AUTHOR_NAME_REGEX


@deconstructible
class PackageReferenceValidator:
    """Validate that a package reference is valid."""

    def __init__(self, require_version: bool = True, resolve: bool = True):
        self.require_version = require_version
        self.resolve = resolve

    def __call__(self, value):
        from thunderstore.repository.package_reference import PackageReference
        try:
            reference = PackageReference.parse(value)
        except ValueError as exc:
            raise ValidationError(str(exc))
        if reference.version is None and self.require_version:
            raise ValidationError(f"Package reference is missing version: {reference}")
        if self.resolve and reference.instance is None:
            raise ValidationError(f"No matching package found for reference: {reference}")

    def __eq__(self, other):
        return all((
            isinstance(other, self.__class__),
            self.require_version == other.require_version,
            self.resolve == other.resolve,
        ))


@deconstructible
class VersionNumberValidator:
    """Validate that a version number string is valid."""

    def __call__(self, value):
        try:
            version = StrictVersion(value)
            correct = ".".join(str(x) for x in version.version)
            if correct != value:
                raise ValidationError(f"Version {value} should be written as {correct}")
        except ValueError as exc:
            raise ValidationError(str(exc))

    def __eq__(self, other):
        return all((
            isinstance(other, self.__class__),
        ))


AuthorNameRegexValidator = RegexValidator(
    regex=AUTHOR_NAME_REGEX,
    message="Author names can only contain a-Z A-Z 0-9 . _ - characers"
)
