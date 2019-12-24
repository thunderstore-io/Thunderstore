import pytest
from django.core.exceptions import ValidationError as DjangoValidationError

from repository.validators import PackageReferenceValidator


@pytest.mark.django_db
def test_reference_validator_resolve_version(package_version):
    validator = PackageReferenceValidator(resolve=True, require_version=True)
    validator(str(package_version.reference))


@pytest.mark.django_db
def test_reference_validator_resolve_versionless(package_version):
    validator = PackageReferenceValidator(resolve=True, require_version=False)
    validator(str(package_version.reference.without_version))


def test_reference_validator_require_version():
    validator = PackageReferenceValidator(resolve=False, require_version=True)
    with pytest.raises(DjangoValidationError):
        validator("someUser-somePackage")
    validator("someUser-somePackage-1.0.0")


def test_reference_validator_allow_versionless():
    validator = PackageReferenceValidator(resolve=False, require_version=False)
    validator("someUser-somePackage")
    validator("someUser-somePackage-1.0.0")
