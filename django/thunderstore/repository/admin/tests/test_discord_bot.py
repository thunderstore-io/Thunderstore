import pytest
from django.conf import settings
from django.test import Client

from thunderstore.core.types import UserType
from thunderstore.repository.models import DiscordUserBotPermission


@pytest.mark.django_db
def test_admin_discord_user_bot_permission_search(admin_client: Client) -> None:
    resp = admin_client.get(
        path="/djangoadmin/repository/discorduserbotpermission/?q=asd",
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_discord_user_bot_permission_list(admin_client: Client) -> None:
    resp = admin_client.get(
        path="/djangoadmin/repository/discorduserbotpermission/",
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_discord_user_bot_permission_detail(
    admin_user: UserType, admin_client: Client
) -> None:
    obj = DiscordUserBotPermission.objects.create(
        label="Test",
        thunderstore_user=admin_user,
        discord_user_id=1234,
        can_deprecate=True,
    )
    path = f"/djangoadmin/repository/discorduserbotpermission/{obj.pk}/change/"
    resp = admin_client.get(
        path=path,
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200
