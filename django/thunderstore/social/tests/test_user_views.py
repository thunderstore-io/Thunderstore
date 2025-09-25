import pytest
from django.test import Client
from django.urls import reverse_lazy

from thunderstore.community.models import CommunitySite
from thunderstore.core.types import UserType


@pytest.mark.django_db
@pytest.mark.parametrize(
    "provider, should_fail", [("discord", False), ("non-existent", True)]
)
def test_disconnect_account(
    client: Client,
    community_site: CommunitySite,
    user_with_social_auths: UserType,
    provider: str,
    should_fail: bool,
):
    client.force_login(user_with_social_auths)

    url = reverse_lazy("settings.linked-accounts")
    response = client.post(
        url,
        HTTP_HOST=community_site.site.domain,
        data={"provider": provider},
        follow=True,
    )

    if should_fail:
        assert response.status_code == 404
        assert response.context["exception"].args == ("Social auth not found",)
    else:
        assert response.status_code == 200
        assert not user_with_social_auths.social_auth.filter(provider=provider).exists()


@pytest.mark.django_db
def test_disconnect_account_unauthenticated(
    client: Client,
    community_site: CommunitySite,
):
    url = reverse_lazy("settings.linked-accounts")
    response = client.post(
        url,
        HTTP_HOST=community_site.site.domain,
        data={"provider": "discord"},
        follow=True,
    )
    assert response.request["PATH_INFO"] == "/"  # redirects back to index


@pytest.mark.django_db
def test_disconnect_account_cannot_disconnect(
    client: Client,
    community_site: CommunitySite,
    user_with_social_auths: UserType,
):
    client.force_login(user_with_social_auths)

    user_with_social_auths.social_auth.filter(provider="discord").delete()

    url = reverse_lazy("settings.linked-accounts")
    response = client.post(
        url,
        HTTP_HOST=community_site.site.domain,
        data={"provider": "github"},
        follow=True,
    )

    assert response.status_code == 200
    assert user_with_social_auths.social_auth.filter(provider="github").exists()
    assert response.context["form"].errors == {
        "__all__": ["Cannot disconnect last linked auth method"]
    }


@pytest.mark.django_db
def test_delete_account_success(
    client: Client,
    community_site: CommunitySite,
    user: UserType,
):
    client.force_login(user)
    user_pk = user.pk

    url = reverse_lazy("settings.delete-account")
    response = client.post(
        url,
        HTTP_HOST=community_site.site.domain,
        data={"verification": user.username},
        follow=True,
    )

    assert response.status_code == 200
    assert not user.__class__.objects.filter(pk=user_pk).exists()


@pytest.mark.django_db
def test_delete_account_invalid_verification(
    client: Client,
    community_site: CommunitySite,
    user: UserType,
):
    client.force_login(user)

    url = reverse_lazy("settings.delete-account")
    response = client.post(
        url,
        HTTP_HOST=community_site.site.domain,
        data={"verification": "wrongusername"},
        follow=True,
    )

    assert response.status_code == 200
    assert response.context["form"].errors == {"verification": ["Invalid verification"]}
    assert user.__class__.objects.filter(pk=user.pk).exists()


@pytest.mark.django_db
def test_delete_account_unauthenticated(
    client: Client,
    community_site: CommunitySite,
):
    url = reverse_lazy("settings.delete-account")
    response = client.post(
        url,
        HTTP_HOST=community_site.site.domain,
        data={"verification": "testuser"},
        follow=True,
    )
    assert response.request["PATH_INFO"] == "/"
