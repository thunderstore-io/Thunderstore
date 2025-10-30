from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from thunderstore.account.models import UserMeta
from thunderstore.community.models import (
    Community,
    CommunityMemberRole,
    CommunityMembership,
)

User = get_user_model()


@pytest.mark.django_db
def test_user_moderated_communities_only_called_once(user: User):
    UserMeta.objects.create(user=user, can_moderate_any_community=True)

    with patch(
        "thunderstore.repository.views.package._utils.get_moderated_communities",
        return_value=["1", "2", "3"],
    ) as mock_get_moderated_communities:

        result1 = user.moderated_communities
        assert result1 == ["1", "2", "3"]
        assert mock_get_moderated_communities.call_count == 1

        result2 = user.moderated_communities
        assert result2 == ["1", "2", "3"]
        assert mock_get_moderated_communities.call_count == 1


@pytest.mark.django_db
def test_user_has_moderated_communities_is_empty_list_by_default(user: User):
    assert hasattr(user, "moderated_communities")
    assert user.moderated_communities == []


@pytest.mark.django_db
def test_anonymous_user_moderated_communities_is_empty_list():
    anon = AnonymousUser()
    assert anon.is_authenticated == False
    assert hasattr(anon, "moderated_communities")
    assert anon.moderated_communities == []


@pytest.mark.django_db
def test_user_moderated_communities_with_user_meta_and_can_moderate(
    user: User, community: Community
):
    CommunityMembership.objects.create(
        user=user, community=community, role=CommunityMemberRole.moderator
    )

    user_meta = UserMeta.objects.get(user=user)
    assert user_meta.can_moderate_any_community == True

    assert hasattr(user, "moderated_communities")
    assert user.moderated_communities == [str(community.id)]


@pytest.mark.django_db
def test_user_moderated_communities_with_user_meta_and_can_not_moderate(
    user: User, community: Community
):
    CommunityMembership.objects.create(
        user=user, community=community, role=CommunityMemberRole.member
    )

    user_meta = UserMeta.objects.get(user=user)
    assert user_meta.can_moderate_any_community == False

    assert hasattr(user, "moderated_communities")
    assert user.moderated_communities == []
