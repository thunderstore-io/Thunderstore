import pytest
from rest_framework import serializers

from rest_framework.exceptions import ValidationError as ValidationError

from repository.factories import PackageVersionFactory
from repository.models import PackageVersion
from repository.package_reference import PackageReference
from repository.serializer_fields import PackageNameField
from repository.serializer_fields import PackageVersionField
from repository.serializer_fields import DependencyField


def test_fields_dependency_invalid_reference():
    field = DependencyField()
    with pytest.raises(ValidationError) as exception:
        field.run_validation("not a reference")
    assert "Invalid package reference string" in str(exception.value)


@pytest.mark.django_db
def test_fields_dependency_missing_version():
    field = DependencyField()
    with pytest.raises(ValidationError) as exception:
        field.run_validation("someUser-somePackage")
    assert "Package reference is missing version" in str(exception.value)


@pytest.mark.django_db
def test_fields_dependency_nonexisting_reference():
    field = DependencyField()
    with pytest.raises(ValidationError) as exception:
        field.run_validation("someUser-somePackage-1.0.0")
    assert "No matching package found for reference" in str(exception.value)


@pytest.mark.django_db
def test_fields_dependency_valid(package_version):
    field = DependencyField()
    result = field.run_validation(package_version.reference)
    assert isinstance(result, PackageReference)
    assert result == package_version.reference


@pytest.mark.django_db
def test_fields_list_dependency_field():
    field = serializers.ListField(
        child=DependencyField(),
        max_length=100,
        allow_empty=True,
    )
    versions = [
        PackageVersionFactory.create(name=f"package_{i}") for i in range(10)
    ]
    references = [
        x.reference for x in versions
    ]
    reference_strings = [
        str(x) for x in references
    ]
    result = field.run_validation(reference_strings)
    assert len(result) == 10
    assert isinstance(result[0], PackageReference)
    assert result == references


@pytest.mark.parametrize(
    "value, exception_message",
    [
        ["some_name", ""],
        ["some-name", "Package names can only contain a-Z A-Z 0-9 _ characers"],
        ["", "This field may not be blank."],
        ["a", ""],
        ["some_very_long_name", ""],
        ["a" * PackageVersion._meta.get_field("name").max_length, ""],
        [
            "a" * PackageVersion._meta.get_field("name").max_length + "b",
            "Ensure this field has no more than 128 characters."
        ],
    ],
)
def test_fields_package_name(value: str, exception_message: str):
    field = PackageNameField()
    if exception_message:
        with pytest.raises(ValidationError) as exception:
            field.run_validation(value)
        assert exception_message in str(exception.value)
    else:
        result = field.run_validation(value)
        assert field.to_representation(result) == value


@pytest.mark.parametrize(
    "value, exception_message",
    [
        ["1.0.0", ""],
        ["1", "Version numbers must follow the Major.Minor.Patch format (e.g. 1.45.320)"],
        ["1.0", "Version numbers must follow the Major.Minor.Patch format (e.g. 1.45.320)"],
        ["1.0.0+a", "Version numbers must follow the Major.Minor.Patch format (e.g. 1.45.320)"],
        ["0.0.0", ""],
        ["-1.0.0", "Version numbers must follow the Major.Minor.Patch format (e.g. 1.45.320)"],
        ["1a.0.0", "Version numbers must follow the Major.Minor.Patch format (e.g. 1.45.320)"],
        ["", "This field may not be blank."],
        ["10000.100000.100", ""],
        ["10000.100000.1000", "Ensure this field has no more than 16 characters."],
    ],
)
def test_fields_package_name(value: str, exception_message: str):
    field = PackageVersionField()
    if exception_message:
        with pytest.raises(ValidationError) as exception:
            field.run_validation(value)
        assert exception_message in str(exception.value)
    else:
        result = field.run_validation(value)
        assert field.to_representation(result) == value
