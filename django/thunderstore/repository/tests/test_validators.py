import copy

import pytest
from django.core.exceptions import ValidationError as DjangoValidationError

from thunderstore.repository.validators import (
    PackageReferenceComponentValidator,
    PackageReferenceValidator,
    VersionNumberValidator,
)


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
    with pytest.raises(DjangoValidationError) as exc:
        validator("someUser-somePackage")
    assert "Package reference is missing version" in str(exc.value)
    validator("someUser-somePackage-1.0.0")


def test_reference_validator_allow_versionless():
    validator = PackageReferenceValidator(resolve=False, require_version=False)
    validator("someUser-somePackage")
    validator("someUser-somePackage-1.0.0")


def test_reference_validator_invalid_reference():
    validator = PackageReferenceValidator(resolve=False, require_version=False)
    with pytest.raises(DjangoValidationError) as exc:
        validator("not a reference")
    assert "Invalid package reference" in str(exc.value)


@pytest.mark.django_db
def test_reference_validator_unresolved():
    validator = PackageReferenceValidator(resolve=True, require_version=True)
    with pytest.raises(DjangoValidationError) as exc:
        validator("someUser-somePackage-1.0.0")
    assert "No matching package found for reference" in str(exc.value)


def test_reference_validator_eq():
    validators = [
        PackageReferenceValidator(resolve=True, require_version=True),
        PackageReferenceValidator(resolve=False, require_version=True),
        PackageReferenceValidator(resolve=True, require_version=False),
        PackageReferenceValidator(resolve=False, require_version=False),
    ]
    for index, validator in enumerate(validators):
        for index2, validator2 in enumerate(validators):
            if index != index2:
                assert validator != validator2
            else:
                assert validator == copy.deepcopy(validator2)


@pytest.mark.parametrize(
    "version_str, should_fail",
    [
        ["1.0.0", False],
        ["1.0.0.0", True],
        ["1.a", True],
        ["asd.dsa.asd", True],
        ["0.0.0", False],
        ["1", True],
        ["20.08.210338", True],
    ],
)
def test_version_number_validator(version_str, should_fail):
    validator = VersionNumberValidator()
    if should_fail:
        with pytest.raises(DjangoValidationError):
            validator(version_str)
    else:
        validator(version_str)


def test_version_number_validator_eq():
    validator_1 = VersionNumberValidator()
    validator_2 = VersionNumberValidator()
    assert validator_1 == validator_2


@pytest.mark.parametrize(
    "component, should_fail",
    (
        ("SomeAuthor", False),
        ("Some-Author", True),
        ("Som3-Auth0r", True),
        ("Som3_Auth0r", False),
        ("Some.Author", True),
        ("Some@Author", True),
        ("_", True),
        ("_Asd", True),
        ("Asd_", True),
        ("As_d_", True),
        ("As_d", False),
        ("26", False),
    ),
)
def test_package_reference_component_validator(component: str, should_fail: bool):
    validator = PackageReferenceComponentValidator("Component")
    if should_fail:
        with pytest.raises(DjangoValidationError):
            validator(component)
    else:
        validator(component)
