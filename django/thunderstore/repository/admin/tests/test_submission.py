import pytest
from django.conf import settings
from django.test import Client

from thunderstore.repository.factories import AsyncPackageSubmissionFactory


@pytest.mark.django_db
def test_admin_asyncpackagesubmission_search(admin_client: Client) -> None:
    username = AsyncPackageSubmissionFactory().owner.username
    resp = admin_client.get(
        path=f"/djangoadmin/repository/asyncpackagesubmission/?q={username}",
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_asyncpackagesubmission_list(admin_client: Client) -> None:
    AsyncPackageSubmissionFactory()
    resp = admin_client.get(
        path="/djangoadmin/repository/asyncpackagesubmission/",
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_asyncpackagesubmission_detail(admin_client: Client) -> None:
    pk = AsyncPackageSubmissionFactory().pk
    path = f"/djangoadmin/repository/asyncpackagesubmission/{pk}/change/"
    resp = admin_client.get(
        path=path,
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200
