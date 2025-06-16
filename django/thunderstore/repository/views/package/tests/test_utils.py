import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Permission

from thunderstore.community.models import (
    Community,
    CommunityMemberRole,
    CommunityMembership,
)
from thunderstore.core.types import UserType
from thunderstore.repository.views.package._utils import get_moderated_communities

User = get_user_model()


@pytest.mark.django_db
def test_utils_get_moderated_communities_no_user(
    community: Community,
):
    assert get_moderated_communities(None) == []
    assert get_moderated_communities(AnonymousUser()) == []


@pytest.mark.django_db
def test_utils_get_moderated_communities_superuser(
    community: Community,
    user: UserType,
):
    user.is_superuser = True
    user.save()
    assert get_moderated_communities(user) == [str(community.pk)]


@pytest.mark.django_db
def test_utils_get_moderated_communities_staff(
    community: Community,
    user: UserType,
):
    user.is_staff = True
    user.save()
    assert get_moderated_communities(user) == []

    perm = Permission.objects.get(
        content_type__app_label="community",
        codename="change_packagelisting",
    )
    user.user_permissions.add(perm)
    user = User.objects.get(pk=user.pk)
    assert get_moderated_communities(user) == [str(community.pk)]


@pytest.mark.django_db
@pytest.mark.parametrize("role", CommunityMemberRole.options())
def test_utils_get_moderated_communities_community_member(
    community: Community,
    user: UserType,
    role: str,
):
    assert get_moderated_communities(user) == []

    membership = CommunityMembership.objects.create(
        user=user,
        community=community,
        role=role,
    )

    expected = (
        [str(community.pk)]
        if role in (CommunityMemberRole.owner, CommunityMemberRole.moderator)
        else []
    )

    assert get_moderated_communities(user) == expected
