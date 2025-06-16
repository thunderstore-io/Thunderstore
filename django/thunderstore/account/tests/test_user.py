from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

User = get_user_model()


@pytest.mark.django_db
def test_user_moderated_communities_only_called_once():
    user = User.objects.create_user(username="tester", password="pass")

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
def test_user_has_moderated_communities_property():
    user = User()
    assert hasattr(user, "moderated_communities")
    assert callable(getattr(User, "moderated_communities").fget)


@pytest.mark.django_db
def test_anonymous_user_moderated_communities_is_empty_list():
    anon = AnonymousUser()
    assert hasattr(anon, "moderated_communities")
    assert anon.moderated_communities == []
