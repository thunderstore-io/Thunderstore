import pytest

from thunderstore.api.cyberstorm.serializers import (
    ModeratorNoteCreateSerializer,
    ModeratorNoteSerializer,
    ModeratorNoteUpdateSerializer,
)
from thunderstore.community.consts import ModeratorNoteTargetType
from thunderstore.community.factories import (
    CommunityFactory,
    ModeratorNoteFactory,
    PackageListingFactory,
)


@pytest.mark.django_db
def test_serializer_output_for_community_note():
    note = ModeratorNoteFactory(community=CommunityFactory(), content="Heads up")

    data = ModeratorNoteSerializer(note).data

    assert data["id"] == note.pk
    assert data["target_type"] == ModeratorNoteTargetType.community
    assert data["content"] == "Heads up"
    assert data["version_number"] is None
    assert data["is_active"] is True
    assert set(data.keys()) == {
        "id",
        "target_type",
        "content",
        "version_number",
        "is_active",
        "datetime_created",
        "datetime_updated",
    }
    # Authorship must never leak into the public payload.
    assert "author" not in data
    assert "author_username" not in data


@pytest.mark.django_db
def test_serializer_output_for_version_note():
    listing = PackageListingFactory()
    version = listing.package.versions.first()
    note = ModeratorNoteFactory(package_listing=listing, package_version=version)

    data = ModeratorNoteSerializer(note).data

    assert data["target_type"] == ModeratorNoteTargetType.version
    assert data["version_number"] == version.version_number


def test_create_serializer_requires_content():
    serializer = ModeratorNoteCreateSerializer(data={})
    assert not serializer.is_valid()
    assert serializer.errors == {"content": ["This field is required."]}


def test_update_serializer_allows_empty_partial_update():
    # Update is a partial update: omitting content is valid.
    serializer = ModeratorNoteUpdateSerializer(data={})
    assert serializer.is_valid()
    assert serializer.validated_data == {}


def test_update_serializer_accepts_is_active():
    serializer = ModeratorNoteUpdateSerializer(data={"is_active": False})
    assert serializer.is_valid()
    assert serializer.validated_data == {"is_active": False}


@pytest.mark.parametrize(
    "serializer_class",
    [
        ModeratorNoteCreateSerializer,
        ModeratorNoteUpdateSerializer,
    ],
)
def test_write_serializer_rejects_blank_content(serializer_class):
    serializer = serializer_class(data={"content": ""})
    assert not serializer.is_valid()
    assert "content" in serializer.errors


@pytest.mark.parametrize(
    "serializer_class",
    [
        ModeratorNoteCreateSerializer,
        ModeratorNoteUpdateSerializer,
    ],
)
def test_write_serializer_accepts_content(serializer_class):
    serializer = serializer_class(data={"content": "A note"})
    assert serializer.is_valid()
    assert serializer.validated_data == {"content": "A note"}
