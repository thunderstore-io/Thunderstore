import base64

import pytest
from rest_framework import serializers
from rest_framework.exceptions import ValidationError as ValidationError

from thunderstore.repository.factories import (
    PackageFactory,
    PackageVersionFactory,
    TeamFactory,
)
from thunderstore.repository.models import PackageVersion
from thunderstore.repository.package_reference import PackageReference
from thunderstore.repository.serializer_fields import (
    Base64Field,
    DependencyField,
    ModelChoiceField,
    PackageNameField,
    PackageVersionField,
    StrictCharField,
)


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
    assert field.to_representation(result) == str(package_version.reference)


@pytest.mark.django_db
def test_fields_list_dependency_field():
    field = serializers.ListField(
        child=DependencyField(),
        max_length=250,
        allow_empty=True,
    )
    team = TeamFactory.create(name="tester")
    versions = [
        PackageVersionFactory.create(
            package=PackageFactory.create(owner=team, name=f"package_{i}"),
            name=f"package_{i}",
        )
        for i in range(10)
    ]
    references = [x.reference for x in versions]
    reference_strings = [str(x) for x in references]
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
            "Ensure this field has no more than 128 characters.",
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
        [
            "1",
            "Version numbers must follow the Major.Minor.Patch format (e.g. 1.45.320)",
        ],
        [
            "1.0",
            "Version numbers must follow the Major.Minor.Patch format (e.g. 1.45.320)",
        ],
        [
            "1.0.0+a",
            "Version numbers must follow the Major.Minor.Patch format (e.g. 1.45.320)",
        ],
        ["0.0.0", ""],
        [
            "-1.0.0",
            "Version numbers must follow the Major.Minor.Patch format (e.g. 1.45.320)",
        ],
        [
            "1a.0.0",
            "Version numbers must follow the Major.Minor.Patch format (e.g. 1.45.320)",
        ],
        ["", "This field may not be blank."],
        ["10000.100000.100", ""],
        ["10000.100000.1000", "Ensure this field has no more than 16 characters."],
    ],
)
def test_fields_package_version(value: str, exception_message: str):
    field = PackageVersionField()
    if exception_message:
        with pytest.raises(ValidationError) as exception:
            field.run_validation(value)
        assert exception_message in str(exception.value)
    else:
        result = field.run_validation(value)
        assert field.to_representation(result) == value


def test_fields_model_choice_field_not_none():
    field = ModelChoiceField(
        queryset=PackageVersion.objects.all(),
        to_field="name",
    )
    with pytest.raises(ValidationError) as e:
        field.run_validation(None)
    assert "This field may not be null" in str(e.value)


@pytest.mark.django_db
def test_fields_model_choice_field_not_found():
    field = ModelChoiceField(
        queryset=PackageVersion.objects.none(),
        to_field="name",
    )
    with pytest.raises(ValidationError) as e:
        field.to_internal_value("somepackage")
    assert "Object not found" in str(e.value)


@pytest.mark.django_db
def test_fields_model_choice_field_to_internal(package_version: PackageVersion):
    field = ModelChoiceField(
        queryset=PackageVersion.objects.all(),
        to_field="name",
    )
    internal = field.to_internal_value(package_version.name)
    assert internal == package_version


@pytest.mark.django_db
def test_fields_model_choice_field_to_representation(package_version: PackageVersion):
    field = ModelChoiceField(
        queryset=PackageVersion.objects.all(),
        to_field="name",
    )
    representation = field.to_representation(package_version)
    assert representation == package_version.name


def test_fields_base64_field_to_internal() -> None:
    field = Base64Field()
    testvalue = b"Testing"
    internal = field.to_internal_value(base64.b64encode(testvalue).decode("utf-8"))
    assert internal == testvalue


def test_fields_base64_field_to_representation() -> None:
    field = Base64Field()
    testvalue = b"Testing"
    representation = field.to_representation(testvalue)
    assert representation == base64.b64encode(testvalue).decode("utf-8")


@pytest.mark.parametrize("required", (True, False))
def test_fields_base64_field_required(required: bool) -> None:
    field = Base64Field(required=required)
    if required:
        with pytest.raises(
            serializers.ValidationError, match="This field is required."
        ):
            field.to_internal_value(None)
    else:
        assert field.to_internal_value(None) is None


def test_fields_base64_field_invalid_base64() -> None:
    field = Base64Field()
    with pytest.raises(serializers.ValidationError, match="Invalid base64 string."):
        field.to_internal_value("¤!#)=(")


def test_fields_base64_field_too_big_value() -> None:
    field = Base64Field(max_size=10)
    testvalue = base64.b64encode(bytearray(11)).decode("utf-8")
    with pytest.raises(
        serializers.ValidationError,
        match="Ensure this field has encoded at most 10 bytes.",
    ):
        field.to_internal_value(testvalue)


def test_fields_base64_field_too_small_value() -> None:
    field = Base64Field(min_size=10)
    testvalue = base64.b64encode(bytearray(9)).decode("utf-8")
    with pytest.raises(
        serializers.ValidationError,
        match="Ensure this field has encoded at least 10 bytes.",
    ):
        field.to_internal_value(testvalue)


@pytest.mark.parametrize("testvalue", (42, 42.432, False, True))
def test_fields_strict_char_field_fail(testvalue) -> None:
    field = StrictCharField()
    with pytest.raises(
        serializers.ValidationError,
        match="Not a valid string.",
    ):
        field.to_internal_value(testvalue)


def test_fields_strict_char_field_success() -> None:
    field = StrictCharField()
    assert field.to_internal_value("test") == "test"
