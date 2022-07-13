import pytest
from django.conf import settings
from django.test import Client

from thunderstore.repository.models import Team


@pytest.mark.django_db
def test_admin_team_search(admin_client: Client) -> None:
    resp = admin_client.get(
        path="/djangoadmin/repository/team/?q=asd",
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_team_list(admin_client: Client) -> None:
    resp = admin_client.get(
        path="/djangoadmin/repository/team/",
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_team_detail(
    team: Team,
    admin_client: Client,
) -> None:
    path = f"/djangoadmin/repository/team/{team.pk}/change/"
    resp = admin_client.get(
        path=path,
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200
