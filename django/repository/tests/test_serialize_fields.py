import pytest
from rest_framework.exceptions import ValidationError

from repository.models import PackageVersion
from repository.serializer_fields import PackageNameField
from repository.serializer_fields import PackageVersionField


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
