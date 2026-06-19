import pytest
from django.core.exceptions import ValidationError

from conftest import TestUserTypes
from thunderstore.api.cyberstorm.services.moderator_note import (
    create_community_moderator_note,
    create_listing_moderator_note,
    create_version_moderator_note,
    delete_moderator_note,
    update_moderator_note,
)
from thunderstore.community.consts import ModeratorNoteTargetType
from thunderstore.community.factories import (
    CommunityFactory,
    ModeratorNoteFactory,
    PackageListingFactory,
)
from thunderstore.community.models import (
    CommunityMemberRole,
    CommunityMembership,
    ModeratorNote,
)
from thunderstore.core.exceptions import PermissionValidationError
from thunderstore.core.factories import UserFactory

MODERATE_MATRIX = [
    (TestUserTypes.no_user, False),
    (TestUserTypes.unauthenticated, False),
    (TestUserTypes.regular_user, False),
    (TestUserTypes.deactivated_user, False),
    (TestUserTypes.service_account, False),
    (TestUserTypes.site_admin, True),
    (TestUserTypes.superuser, True),
]


def _make_community_moderator(community):
    user = UserFactory()
    CommunityMembership.objects.create(
        user=user,
        community=community,
        role=CommunityMemberRole.moderator,
    )
    return user


@pytest.mark.django_db
@pytest.mark.parametrize("user_role, can_moderate", MODERATE_MATRIX)
def test_create_community_moderator_note(user_role, can_moderate):
    community = CommunityFactory()
    agent = TestUserTypes.get_user_by_type(user_role)

    if not can_moderate:
        with pytest.raises(PermissionValidationError):
            create_community_moderator_note(
                agent=agent, community=community, content="Heads up"
            )
        assert not ModeratorNote.objects.exists()
    else:
        note = create_community_moderator_note(
            agent=agent, community=community, content="Heads up"
        )
        assert note.community == community
        assert note.author == agent
        assert note.target_type == ModeratorNoteTargetType.community


@pytest.mark.django_db
@pytest.mark.parametrize("user_role, can_moderate", MODERATE_MATRIX)
def test_create_listing_moderator_note(user_role, can_moderate):
    listing = PackageListingFactory()
    agent = TestUserTypes.get_user_by_type(user_role)

    if not can_moderate:
        with pytest.raises(PermissionValidationError):
            create_listing_moderator_note(
                agent=agent, listing=listing, content="Known issue"
            )
        assert not ModeratorNote.objects.exists()
    else:
        note = create_listing_moderator_note(
            agent=agent, listing=listing, content="Known issue"
        )
        assert note.package_listing == listing
        assert note.target_type == ModeratorNoteTargetType.listing


@pytest.mark.django_db
@pytest.mark.parametrize("user_role, can_moderate", MODERATE_MATRIX)
def test_create_version_moderator_note(user_role, can_moderate):
    listing = PackageListingFactory()
    version = listing.package.versions.first()
    agent = TestUserTypes.get_user_by_type(user_role)

    if not can_moderate:
        with pytest.raises(PermissionValidationError):
            create_version_moderator_note(
                agent=agent, listing=listing, version=version, content="Broken"
            )
        assert not ModeratorNote.objects.exists()
    else:
        note = create_version_moderator_note(
            agent=agent, listing=listing, version=version, content="Broken"
        )
        assert note.package_listing == listing
        assert note.package_version == version
        assert note.target_type == ModeratorNoteTargetType.version


@pytest.mark.django_db
def test_create_version_moderator_note_rejects_foreign_version():
    listing = PackageListingFactory()
    other_version = PackageListingFactory().package.versions.first()
    agent = TestUserTypes.get_user_by_type(TestUserTypes.superuser)

    with pytest.raises(ValidationError):
        create_version_moderator_note(
            agent=agent, listing=listing, version=other_version, content="Broken"
        )
    assert not ModeratorNote.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize("user_role, can_moderate", MODERATE_MATRIX)
def test_update_moderator_note(user_role, can_moderate):
    note = ModeratorNoteFactory(community=CommunityFactory(), content="Original")
    agent = TestUserTypes.get_user_by_type(user_role)

    if not can_moderate:
        with pytest.raises(PermissionValidationError):
            update_moderator_note(agent=agent, note=note, content="Edited")
        note.refresh_from_db()
        assert note.content == "Original"
    else:
        update_moderator_note(agent=agent, note=note, content="Edited")
        note.refresh_from_db()
        assert note.content == "Edited"


@pytest.mark.django_db
@pytest.mark.parametrize("user_role, can_moderate", MODERATE_MATRIX)
def test_delete_moderator_note(user_role, can_moderate):
    note = ModeratorNoteFactory(community=CommunityFactory())
    agent = TestUserTypes.get_user_by_type(user_role)

    if not can_moderate:
        with pytest.raises(PermissionValidationError):
            delete_moderator_note(agent=agent, note=note)
        assert ModeratorNote.objects.filter(pk=note.pk).exists()
    else:
        delete_moderator_note(agent=agent, note=note)
        assert not ModeratorNote.objects.filter(pk=note.pk).exists()


@pytest.mark.django_db
def test_community_moderator_can_manage_own_community_note():
    community = CommunityFactory()
    moderator = _make_community_moderator(community)
    note = ModeratorNoteFactory(community=community, content="Original")

    update_moderator_note(agent=moderator, note=note, content="Edited")
    note.refresh_from_db()
    assert note.content == "Edited"

    delete_moderator_note(agent=moderator, note=note)
    assert not ModeratorNote.objects.filter(pk=note.pk).exists()


@pytest.mark.django_db
def test_community_moderator_cannot_manage_other_community_note():
    moderator = _make_community_moderator(CommunityFactory())
    foreign_note = ModeratorNoteFactory(community=CommunityFactory())

    with pytest.raises(PermissionValidationError):
        update_moderator_note(agent=moderator, note=foreign_note, content="Edited")

    with pytest.raises(PermissionValidationError):
        delete_moderator_note(agent=moderator, note=foreign_note)

    assert ModeratorNote.objects.filter(pk=foreign_note.pk).exists()


@pytest.mark.django_db
def test_listing_moderator_authority_is_scoped_to_listing_community():
    listing = PackageListingFactory()
    foreign_moderator = _make_community_moderator(CommunityFactory())

    with pytest.raises(PermissionValidationError):
        create_listing_moderator_note(
            agent=foreign_moderator, listing=listing, content="Nope"
        )
    assert not ModeratorNote.objects.exists()


@pytest.mark.django_db
def test_version_moderator_authority_is_scoped_to_listing_community():
    listing = PackageListingFactory()
    version = listing.package.versions.first()
    foreign_moderator = _make_community_moderator(CommunityFactory())

    with pytest.raises(PermissionValidationError):
        create_version_moderator_note(
            agent=foreign_moderator, listing=listing, version=version, content="No"
        )
    assert not ModeratorNote.objects.exists()


@pytest.mark.django_db
def test_community_moderator_cannot_manage_other_community_version_note():
    listing = PackageListingFactory()
    version = listing.package.versions.first()
    note = ModeratorNoteFactory(package_listing=listing, package_version=version)
    foreign_moderator = _make_community_moderator(CommunityFactory())

    with pytest.raises(PermissionValidationError):
        update_moderator_note(agent=foreign_moderator, note=note, content="Edited")
    with pytest.raises(PermissionValidationError):
        delete_moderator_note(agent=foreign_moderator, note=note)

    assert ModeratorNote.objects.filter(pk=note.pk).exists()


# --- Single active note per resource ------------------------------------------


@pytest.mark.django_db
def test_create_community_note_keeps_previous_active():
    community = CommunityFactory()
    agent = TestUserTypes.get_user_by_type(TestUserTypes.superuser)

    first = create_community_moderator_note(
        agent=agent, community=community, content="First"
    )
    second = create_community_moderator_note(
        agent=agent, community=community, content="Second"
    )

    first.refresh_from_db()
    # Multiple active notes coexist; creating one never deactivates another.
    assert first.is_active is True
    assert second.is_active is True
    assert (
        ModeratorNote.objects.filter(community=community, is_active=True).count() == 2
    )


@pytest.mark.django_db
def test_create_listing_note_keeps_previous_active():
    listing = PackageListingFactory()
    agent = TestUserTypes.get_user_by_type(TestUserTypes.superuser)

    first = create_listing_moderator_note(agent=agent, listing=listing, content="First")
    create_listing_moderator_note(agent=agent, listing=listing, content="Second")

    first.refresh_from_db()
    assert first.is_active is True
    assert listing.moderator_notes.filter(is_active=True).count() == 2


@pytest.mark.django_db
def test_update_can_deactivate_note():
    agent = TestUserTypes.get_user_by_type(TestUserTypes.superuser)
    note = ModeratorNoteFactory(community=CommunityFactory())

    update_moderator_note(agent=agent, note=note, is_active=False)
    note.refresh_from_db()
    assert note.is_active is False


@pytest.mark.django_db
def test_update_content_only_leaves_is_active_untouched():
    agent = TestUserTypes.get_user_by_type(TestUserTypes.superuser)
    note = ModeratorNoteFactory(community=CommunityFactory(), is_active=False)

    update_moderator_note(agent=agent, note=note, content="Edited")
    note.refresh_from_db()
    assert note.content == "Edited"
    assert note.is_active is False


@pytest.mark.django_db
def test_update_with_no_fields_is_a_noop():
    agent = TestUserTypes.get_user_by_type(TestUserTypes.superuser)
    note = ModeratorNoteFactory(community=CommunityFactory(), content="Original")

    update_moderator_note(agent=agent, note=note)
    note.refresh_from_db()
    assert note.content == "Original"
    assert note.is_active is True


@pytest.mark.django_db
def test_update_reactivate_does_not_affect_other_notes():
    community = CommunityFactory()
    agent = TestUserTypes.get_user_by_type(TestUserTypes.superuser)
    old = ModeratorNoteFactory(community=community, is_active=False)
    current = ModeratorNoteFactory(community=community)

    update_moderator_note(agent=agent, note=old, is_active=True)

    old.refresh_from_db()
    current.refresh_from_db()
    # Reactivating one note leaves every other note untouched.
    assert old.is_active is True
    assert current.is_active is True
    assert (
        ModeratorNote.objects.filter(community=community, is_active=True).count() == 2
    )
