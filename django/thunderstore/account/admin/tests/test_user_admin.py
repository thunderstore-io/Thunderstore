import pytest
from django.test import Client
from social_django.models import UserSocialAuth

from thunderstore.core import settings
from thunderstore.core.types import UserType


@pytest.mark.django_db
def test_admin_user_list(
    admin_client: Client,
    user: UserType,
) -> None:
    resp = admin_client.get(
        path="/djangoadmin/auth/user/",
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_user_is_service_account_ordering(
    admin_client: Client,
    user: UserType,
) -> None:
    resp = admin_client.get(
        path="/djangoadmin/auth/user/?o=6.1",
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200
    resp = admin_client.get(
        path="/djangoadmin/auth/user/?o=-6.1",
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_user_search_by_social_auth_uid(
    admin_client: Client,
    user: UserType,
) -> None:
    UserSocialAuth.objects.create(user=user, provider="testprovider", uid="hunter2")
    resp = admin_client.get(
        path="/djangoadmin/auth/user/?q=hunter2",
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200
    resp_text = resp.content.decode()
    assert user.username in resp_text
    assert user.email in resp_text


@pytest.mark.django_db
def test_admin_user_detail(
    admin_client: Client,
    user: UserType,
) -> None:
    resp = admin_client.get(
        path=f"/djangoadmin/auth/user/{user.pk}/change/",
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200
