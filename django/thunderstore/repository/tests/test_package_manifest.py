import pytest

from thunderstore.repository.factories import (
    NamespaceFactory,
    PackageFactory,
    PackageVersionFactory,
    TeamFactory,
)
from thunderstore.repository.models import (
    PackageVersion,
    Team,
    TeamMember,
    TeamMemberRole,
)
from thunderstore.repository.package_manifest import ManifestV1Serializer
from thunderstore.repository.package_reference import PackageReference
from thunderstore.repository.validators import PackageReferenceValidator


@pytest.mark.django_db
def test_manifest_v1_serializer_missing_privileges(user, team, manifest_v1_data):
    serializer = ManifestV1Serializer(
        user=user,
        team=team,
        data=manifest_v1_data,
    )
    assert serializer.is_valid() is False
    assert len(serializer.errors["non_field_errors"]) == 1
    assert "Missing privileges to upload under author" in str(
        serializer.errors["non_field_errors"][0]
    )


@pytest.mark.django_db
def test_manifest_v1_serializer_version_already_exists(
    user, manifest_v1_data, package_version
):
    TeamMember.objects.create(
        user=user,
        team=package_version.owner,
        role=TeamMemberRole.owner,
    )
    manifest_v1_data["name"] = package_version.name
    manifest_v1_data["version_number"] = package_version.version_number
    serializer = ManifestV1Serializer(
        user=user,
        team=package_version.owner,
        data=manifest_v1_data,
    )
    assert serializer.is_valid() is False
    assert len(serializer.errors["non_field_errors"]) == 1
    assert "Package of the same namespace, name and version already exists" in str(
        serializer.errors["non_field_errors"][0]
    )


@pytest.mark.django_db
def test_manifest_v1_serializer_duplicate_dependency(
    user, manifest_v1_data, package_version, namespace
):
    TeamMember.objects.create(
        user=user,
        team=package_version.owner,
        role=TeamMemberRole.owner,
    )
    pkg = PackageFactory.create(
        owner=package_version.owner, name="somepackage", namespace=namespace
    )
    version1 = PackageVersionFactory.create(
        package=pkg,
        name="somepackage",
        version_number="1.0.0",
    )
    version2 = PackageVersionFactory.create(
        package=pkg,
        name="somepackage",
        version_number="2.0.0",
    )
    manifest_v1_data["dependencies"] = [
        str(version1.reference),
        str(version2.reference),
    ]
    serializer = ManifestV1Serializer(
        user=user,
        team=package_version.owner,
        data=manifest_v1_data,
    )
    assert serializer.is_valid() is False
    assert len(serializer.errors["non_field_errors"]) == 1
    assert "Cannot depend on multiple versions of the same package" in str(
        serializer.errors["non_field_errors"][0]
    )


@pytest.mark.django_db
def test_manifest_v1_serializer_self_dependency(
    user, manifest_v1_data, package_version
):
    TeamMember.objects.create(
        user=user,
        team=package_version.owner,
        role=TeamMemberRole.owner,
    )
    manifest_v1_data["name"] = package_version.name
    manifest_v1_data["version_number"] = "1" + package_version.version_number
    manifest_v1_data["dependencies"] = [
        str(package_version.reference),
    ]
    serializer = ManifestV1Serializer(
        user=user,
        team=package_version.owner,
        data=manifest_v1_data,
    )
    assert serializer.is_valid() is False
    assert len(serializer.errors["non_field_errors"]) == 1
    assert "Package depending on itself is not allowed" in str(
        serializer.errors["non_field_errors"][0]
    )


@pytest.mark.django_db
def test_manifest_v1_serializer_unresolved_dependency(
    user, manifest_v1_data, package_version
):
    team = Team.get_or_create_for_user(user)
    manifest_v1_data["dependencies"] = [
        "invalid-package-1.0.0",
        str(package_version.reference),
        "invalid-package-2.0.0",
    ]
    serializer = ManifestV1Serializer(
        user=user,
        team=team,
        data=manifest_v1_data,
    )
    assert serializer.is_valid() is False
    assert len(serializer.errors["dependencies"]) == 2
    assert "No matching package found for reference" in str(
        serializer.errors["dependencies"][0]
    )
    assert "No matching package found for reference" in str(
        serializer.errors["dependencies"][2]
    )


@pytest.mark.django_db
def test_manifest_v1_serializer_too_many_dependencies(user, manifest_v1_data):
    team = Team.get_or_create_for_user(user)
    reference_strings = [f"user-package-{i}.{i}.{i}" for i in range(1001)]
    manifest_v1_data["dependencies"] = reference_strings
    serializer = ManifestV1Serializer(
        user=user,
        team=team,
        data=manifest_v1_data,
    )
    # Patch the validator because we don't want to generate 101 actual packages here
    serializer.fields["dependencies"].child.validators = [
        PackageReferenceValidator(
            require_version=True,
            resolve=False,  # Otherwise the same, but don't try to resolve the references
        )
    ]
    assert serializer.is_valid() is False
    assert len(serializer.errors["dependencies"]) == 1
    assert "Ensure this field has no more than 1000 elements." in str(
        serializer.errors["dependencies"][0]
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "name, error",
    [
        ["some_name", ""],
        ["some-name", "Package names can only contain a-Z A-Z 0-9 _ characers"],
        ["", "This field may not be blank."],
        ["a", ""],
        ["some_very_long_name", ""],
        [None, "This field may not be null."],
        ["a" * PackageVersion._meta.get_field("name").max_length, ""],
        [
            "a" * PackageVersion._meta.get_field("name").max_length + "b",
            "Ensure this field has no more than 128 characters.",
        ],
    ],
)
def test_manifest_v1_serializer_name_validation(
    user, manifest_v1_data, name: str, error: str
):
    team = Team.get_or_create_for_user(user)
    manifest_v1_data["name"] = name
    serializer = ManifestV1Serializer(
        user=user,
        team=team,
        data=manifest_v1_data,
    )
    if error:
        assert serializer.is_valid() is False
        assert error in str(serializer.errors["name"][0])
    else:
        assert serializer.is_valid() is True


@pytest.mark.django_db
@pytest.mark.parametrize(
    "version, error",
    [
        ["1.0.0", ""],
        [
            "asdasdasd",
            "Version numbers must follow the Major.Minor.Patch format (e.g. 1.45.320)",
        ],
        ["", "This field may not be blank."],
        ["1.5.2", ""],
        [
            "1.6.2+post.dev1",
            "Version numbers must follow the Major.Minor.Patch format (e.g. 1.45.320)",
        ],
        ["11111.111111.111", ""],
        [None, "This field may not be null."],
        ["111111.111111.111", "Ensure this field has no more than 16 characters."],
    ],
)
def test_manifest_v1_serializer_version_number_validation(
    user, manifest_v1_data, version: str, error: str
):
    team = Team.get_or_create_for_user(user)
    manifest_v1_data["version_number"] = version
    serializer = ManifestV1Serializer(
        user=user,
        team=team,
        data=manifest_v1_data,
    )
    if error:
        assert serializer.is_valid() is False
        assert error in str(serializer.errors["version_number"][0])
    else:
        assert serializer.is_valid() is True


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url, error",
    [
        ["asdiasdhuasd", ""],
        ["https://google.com/", ""],
        ["", ""],
        ["a", ""],
        ["some not valid website URL", ""],
        [None, "This field may not be null."],
        ["a" * PackageVersion._meta.get_field("website_url").max_length, ""],
        [
            "a" * PackageVersion._meta.get_field("website_url").max_length + "b",
            "Ensure this field has no more than 1024 characters.",
        ],
    ],
)
def test_manifest_v1_serializer_website_url_validation(
    user, manifest_v1_data, url: str, error: str
):
    team = Team.get_or_create_for_user(user)
    manifest_v1_data["website_url"] = url
    serializer = ManifestV1Serializer(
        user=user,
        team=team,
        data=manifest_v1_data,
    )
    if error:
        assert serializer.is_valid() is False
        assert error in str(serializer.errors["website_url"][0])
    else:
        assert serializer.is_valid() is True


@pytest.mark.django_db
@pytest.mark.parametrize(
    "description, error",
    [
        ["asdiasdhuasd", ""],
        ["https://google.com/", ""],
        ["", ""],
        ["a", ""],
        ["some not valid website URL", ""],
        [None, "This field may not be null."],
        ["a" * PackageVersion._meta.get_field("description").max_length, ""],
        [
            "a" * PackageVersion._meta.get_field("description").max_length + "b",
            "Ensure this field has no more than 256 characters.",
        ],
    ],
)
def test_manifest_v1_serializer_description_validation(
    user, manifest_v1_data, description: str, error: str
):
    team = Team.get_or_create_for_user(user)
    manifest_v1_data["description"] = description
    serializer = ManifestV1Serializer(
        user=user,
        team=team,
        data=manifest_v1_data,
    )
    if error:
        assert serializer.is_valid() is False
        assert error in str(serializer.errors["description"][0])
    else:
        assert serializer.is_valid() is True


@pytest.mark.django_db
@pytest.mark.parametrize(
    "dependencies, error",
    [
        [["asdiasdhuasd"], "Invalid package reference string"],
        [["https://google.com/"], "Invalid package reference string"],
        [[""], "Invalid package reference string"],
        [["a"], "Invalid package reference string"],
        [["some not valid website URL"], "Invalid package reference string"],
        [[None], "This field may not be null."],
        [None, "This field may not be null."],
        ["", 'Expected a list of items but got type "str".'],
    ],
)
def test_manifest_v1_serializer_dependencies_invalid(
    user, manifest_v1_data, dependencies, error: str
):
    team = Team.get_or_create_for_user(user)
    manifest_v1_data["dependencies"] = dependencies
    serializer = ManifestV1Serializer(
        user=user,
        team=team,
        data=manifest_v1_data,
    )
    if error:
        assert serializer.is_valid() is False
        assert error in str(serializer.errors["dependencies"][0])
    else:
        assert serializer.is_valid() is True


def test_manifest_v1_serializer_dependencies_valid(user, manifest_v1_data):
    reference = PackageReference.parse("actual_package-reference-1.0.0")
    owner = TeamFactory.create(name=reference.namespace)
    namespace = NamespaceFactory.create(name=owner.name, team=owner)
    PackageVersionFactory.create(
        package=PackageFactory.create(
            owner=owner,
            name=reference.name,
            namespace=namespace,
        ),
        name=reference.name,
        version_number=reference.version_str,
    )
    team = Team.get_or_create_for_user(user)
    manifest_v1_data["dependencies"] = [str(reference)]
    serializer = ManifestV1Serializer(
        user=user,
        team=team,
        data=manifest_v1_data,
    )
    assert serializer.is_valid() is True


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field",
    [
        "name",
        "version_number",
        "website_url",
        "description",
        "dependencies",
    ],
)
def test_manifest_v1_missing_fields(user, manifest_v1_data, field):
    team = Team.get_or_create_for_user(user)
    del manifest_v1_data[field]
    serializer = ManifestV1Serializer(
        user=user,
        team=team,
        data=manifest_v1_data,
    )
    assert serializer.is_valid() is False
    assert "This field is required." in str(serializer.errors[field][0])


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field",
    [
        "name",
        "version_number",
        "website_url",
        "description",
        "dependencies",
    ],
)
def test_manifest_v1_null_fields(user, manifest_v1_data, field):
    team = Team.get_or_create_for_user(user)
    manifest_v1_data[field] = None
    serializer = ManifestV1Serializer(
        user=user,
        team=team,
        data=manifest_v1_data,
    )
    assert serializer.is_valid() is False
    assert "This field may not be null." in str(serializer.errors[field][0])


@pytest.mark.django_db
@pytest.mark.parametrize("fieldname", ("description", "website_url"))
@pytest.mark.parametrize("testdata", (42, 42.432, False, True))
def test_manifest_v1_strict_char_fields(user, manifest_v1_data, fieldname, testdata):
    team = Team.get_or_create_for_user(user)
    manifest_v1_data[fieldname] = testdata
    serializer = ManifestV1Serializer(
        user=user,
        team=team,
        data=manifest_v1_data,
    )
    assert serializer.is_valid() is False
    assert "Not a valid string." in str(serializer.errors[fieldname][0])


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field, empty_val, should_fail",
    [
        ["name", "", True],
        ["version_number", "", True],
        ["website_url", "", False],
        ["description", "", False],
        ["dependencies", [], False],
    ],
)
def test_manifest_v1_blank_fields(
    user, manifest_v1_data, field, empty_val, should_fail
):
    team = Team.get_or_create_for_user(user)
    manifest_v1_data[field] = empty_val
    serializer = ManifestV1Serializer(
        user=user,
        team=team,
        data=manifest_v1_data,
    )
    if should_fail:
        assert serializer.is_valid() is False
        assert "This field may not be blank." in str(serializer.errors[field][0])
    else:
        assert serializer.is_valid() is True


def test_manifest_v1_requires_user(manifest_v1_data):
    with pytest.raises(AttributeError) as exc:
        _ = ManifestV1Serializer(
            data=manifest_v1_data,
        )
    assert "Missing required key word parameter: user" in str(exc.value)


def test_manifest_v1_requires_team(user, manifest_v1_data):
    with pytest.raises(AttributeError) as exc:
        _ = ManifestV1Serializer(
            data=manifest_v1_data,
            user=user,
        )
    assert "Missing required key word parameter: team" in str(exc.value)


def test_manifest_v1_create(user, manifest_v1_data):
    team = Team.get_or_create_for_user(user)
    serializer = ManifestV1Serializer(
        user=user,
        team=team,
        data=manifest_v1_data,
    )
    assert serializer.is_valid()
    with pytest.raises(NotImplementedError) as exc:
        serializer.create(serializer.validated_data)
    assert ".create() is not supported" in str(exc.value)


def test_manifest_v1_update(user, manifest_v1_data):
    team = Team.get_or_create_for_user(user)
    serializer = ManifestV1Serializer(
        user=user,
        team=team,
        data=manifest_v1_data,
    )
    assert serializer.is_valid()
    with pytest.raises(NotImplementedError) as exc:
        serializer.update({}, serializer.validated_data)
    assert ".update() is not supported" in str(exc.value)


def test_manifest_v1_deserialize_serialize(user, manifest_v1_data, package_version):
    team = Team.get_or_create_for_user(user)
    manifest_v1_data["dependencies"] = [str(package_version.reference)]
    deserializer = ManifestV1Serializer(
        user=user,
        team=team,
        data=manifest_v1_data,
    )
    assert deserializer.is_valid()
    validated_data = deserializer.validated_data
    assert validated_data
    assert isinstance(validated_data["dependencies"][0], PackageReference)
    assert validated_data["dependencies"][0] == package_version.reference
    serializer = ManifestV1Serializer(
        instance=validated_data,
        user=user,
        team=team,
    )
    serialized_data = serializer.data
    assert serialized_data == manifest_v1_data


def test_manifest_v1_invalid_key_formatting(user):
    data = {
        "name": "name",
        "versionNumber": "1.0.0",
        "websiteUrl": "",
        "description": "",
        "dependencies": [],
    }
    team = Team.get_or_create_for_user(user)
    deserializer = ManifestV1Serializer(
        user=user,
        team=team,
        data=data,
    )
    assert deserializer.is_valid() is False
