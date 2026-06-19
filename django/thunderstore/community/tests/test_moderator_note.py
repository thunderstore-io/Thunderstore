from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone

from thunderstore.community.consts import ModeratorNoteTargetType
from thunderstore.community.factories import (
    CommunityFactory,
    ModeratorNoteFactory,
    PackageListingFactory,
)
from thunderstore.community.models import ModeratorNote
from thunderstore.core.factories import UserFactory


def _version_for(listing):
    return listing.package.versions.first()


@pytest.mark.django_db
def test_create_community_note():
    community = CommunityFactory()
    note = ModeratorNoteFactory(community=community)

    assert note.pk is not None
    assert note.target_type == ModeratorNoteTargetType.community
    assert note.relevant_community == community
    assert note.version_number is None


@pytest.mark.django_db
def test_create_listing_note():
    listing = PackageListingFactory()
    note = ModeratorNoteFactory(package_listing=listing)

    assert note.target_type == ModeratorNoteTargetType.listing
    assert note.relevant_community == listing.community
    assert note.version_number is None


@pytest.mark.django_db
def test_create_version_note():
    listing = PackageListingFactory()
    version = _version_for(listing)
    note = ModeratorNoteFactory(package_listing=listing, package_version=version)

    assert note.target_type == ModeratorNoteTargetType.version
    assert note.relevant_community == listing.community
    assert note.version_number == version.version_number


@pytest.mark.django_db
def test_validate_rejects_no_target():
    with pytest.raises(ValidationError):
        ModeratorNoteFactory()


@pytest.mark.django_db
def test_validate_rejects_two_targets():
    community = CommunityFactory()
    listing = PackageListingFactory()
    with pytest.raises(ValidationError):
        ModeratorNoteFactory(community=community, package_listing=listing)


@pytest.mark.django_db
def test_validate_rejects_version_without_listing():
    community = CommunityFactory()
    listing = PackageListingFactory()
    version = _version_for(listing)
    # community + version => exactly one *target*, but a version note must also
    # reference its listing.
    with pytest.raises(ValidationError):
        ModeratorNoteFactory(community=community, package_version=version)


@pytest.mark.django_db
def test_validate_rejects_version_listing_package_mismatch():
    listing = PackageListingFactory()
    other_listing = PackageListingFactory()
    other_version = _version_for(other_listing)
    with pytest.raises(ValidationError):
        ModeratorNoteFactory(package_listing=listing, package_version=other_version)


@pytest.mark.django_db
def test_db_constraint_rejects_invalid_target():
    # bulk_create bypasses Model.save()/validate(), so the database
    # CheckConstraint is the last line of defense.
    with pytest.raises(IntegrityError):
        ModeratorNote.objects.bulk_create([ModeratorNote(content="no target")])


@pytest.mark.django_db
def test_author_is_kept_for_audit_but_nulled_on_delete():
    author = UserFactory()
    note = ModeratorNoteFactory(community=CommunityFactory(), author=author)
    assert note.author == author

    author.delete()
    note.refresh_from_db()
    assert note.author is None
    assert ModeratorNote.objects.filter(pk=note.pk).exists()


@pytest.mark.django_db
def test_community_delete_cascades_to_notes():
    community = CommunityFactory()
    note = ModeratorNoteFactory(community=community)
    community.delete()
    assert not ModeratorNote.objects.filter(pk=note.pk).exists()


@pytest.mark.django_db
def test_listing_delete_cascades_to_notes():
    listing = PackageListingFactory()
    note = ModeratorNoteFactory(package_listing=listing)
    listing.delete()
    assert not ModeratorNote.objects.filter(pk=note.pk).exists()


@pytest.mark.django_db
def test_version_delete_cascades_to_notes():
    listing = PackageListingFactory()
    version = _version_for(listing)
    note = ModeratorNoteFactory(package_listing=listing, package_version=version)
    version.delete()
    assert not ModeratorNote.objects.filter(pk=note.pk).exists()


@pytest.mark.django_db
def test_notes_ordered_newest_first():
    community = CommunityFactory()
    older = ModeratorNoteFactory(community=community)
    newer = ModeratorNoteFactory(community=community)
    ModeratorNote.objects.filter(pk=older.pk).update(
        datetime_created=timezone.now() - timedelta(days=1)
    )

    notes = list(ModeratorNote.objects.filter(community=community))
    assert notes == [newer, older]


@pytest.mark.django_db
def test_is_active_defaults_to_true():
    note = ModeratorNoteFactory(community=CommunityFactory())
    assert note.is_active is True


@pytest.mark.django_db
def test_multiple_active_community_notes_allowed():
    community = CommunityFactory()
    ModeratorNoteFactory(community=community)
    ModeratorNoteFactory(community=community)
    assert community.moderator_notes.filter(is_active=True).count() == 2


@pytest.mark.django_db
def test_multiple_active_listing_notes_allowed():
    listing = PackageListingFactory()
    ModeratorNoteFactory(package_listing=listing)
    ModeratorNoteFactory(package_listing=listing)
    assert (
        listing.moderator_notes.filter(
            is_active=True, package_version__isnull=True
        ).count()
        == 2
    )


@pytest.mark.django_db
def test_multiple_active_version_notes_allowed():
    listing = PackageListingFactory()
    version = _version_for(listing)
    ModeratorNoteFactory(package_listing=listing, package_version=version)
    ModeratorNoteFactory(package_listing=listing, package_version=version)
    assert (
        listing.moderator_notes.filter(is_active=True, package_version=version).count()
        == 2
    )


@pytest.mark.django_db
def test_listing_wide_and_version_notes_are_separate_resources():
    listing = PackageListingFactory()
    version = _version_for(listing)
    listing_note = ModeratorNoteFactory(package_listing=listing)
    version_note = ModeratorNoteFactory(
        package_listing=listing, package_version=version
    )

    assert listing_note.is_active is True
    assert version_note.is_active is True


@pytest.mark.django_db
def test_str_includes_target_type():
    note = ModeratorNoteFactory(community=CommunityFactory())
    assert ModeratorNoteTargetType.community in str(note)


def test_relevant_community_is_none_without_target():
    # A target-less instance can never be persisted (validate() blocks it), but
    # the property must still degrade gracefully.
    assert ModeratorNote().relevant_community is None
