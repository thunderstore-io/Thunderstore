import pytest

from repository.models import PackageVersion
from repository.package_validation import validate_field_name


NAME_MAX_LEN = PackageVersion._meta.get_field("version_number").max_length


@pytest.mark.parametrize(
    "name, errors",
    [
        (None, ["The manifest field 'name' is missing"]),
        (NAME_MAX_LEN * "lol", ["The manifest field 'name' is too long"]),
        ("invalid-name", ["Package names can only contain a-Z A-Z 0-9 _ characers"]),
        (
            "invalid-and-long" * NAME_MAX_LEN,
            [
                "The manifest field 'name' is too long",
                "Package names can only contain a-Z A-Z 0-9 _ characers",
            ],
        ),
        ("someValidName", []),
    ],
)
def test_validate_field_name(name, errors):
    validation_errors = validate_field_name(name)
    assert len(errors) == len(validation_errors)
    error_messages = [e.message for e in validation_errors]
    for error in errors:
        assert error in error_messages
