import pytest
from django.contrib.auth import get_user_model

from thunderstore.account.models import UserMeta
from thunderstore.community.models import (
    Community,
    CommunityMemberRole,
    CommunityMembership,
)

User = get_user_model()


@pytest.mark.django_db
def test_user_meta_created_and_updated_for_moderator_role(
    user: User, community: Community
):
    meta = UserMeta.create_or_update(user=user)
    assert meta.can_moderate_any_community is False

    CommunityMembership.objects.create(
        user=user, community=community, role=CommunityMemberRole.moderator
    )

    meta = UserMeta.create_or_update(user=user)
    assert meta.can_moderate_any_community is True


@pytest.mark.django_db
def test_user_meta_false_when_no_moderation_roles(user: User, community: Community):
    CommunityMembership.objects.create(
        user=user, community=community, role=CommunityMemberRole.member
    )

    meta = UserMeta.create_or_update(user=user)
    assert meta.can_moderate_any_community is False


@pytest.mark.django_db
def test_user_meta_updates_when_role_removed(user: User, community: Community):
    membership = CommunityMembership.objects.create(
        user=user, community=community, role=CommunityMemberRole.janitor
    )
    UserMeta.create_or_update(user=user)

    assert UserMeta.objects.get(user=user).can_moderate_any_community is True

    membership.delete()

    meta = UserMeta.create_or_update(user=user)
    assert meta.can_moderate_any_community is False


@pytest.mark.django_db
def test_user_meta_updates_when_role_changed(user: User, community: Community):
    membership = CommunityMembership.objects.create(
        user=user, community=community, role=CommunityMemberRole.owner
    )
    UserMeta.create_or_update(user=user)
    assert UserMeta.objects.get(user=user).can_moderate_any_community is True

    membership.role = CommunityMemberRole.member
    membership.save()

    meta = UserMeta.objects.get(user=user)
    assert meta.can_moderate_any_community is False
