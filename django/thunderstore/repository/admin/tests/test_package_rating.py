import pytest
from django.conf import settings
from django.test import Client

from thunderstore.repository.factories import PackageRatingFactory


@pytest.mark.django_db
def test_admin_package_rating_search(admin_client: Client) -> None:
    resp = admin_client.get(
        path="/djangoadmin/repository/packagerating/?q=asd",
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_package_rating_list(admin_client: Client) -> None:
    resp = admin_client.get(
        path="/djangoadmin/repository/packagerating/",
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_package_rating_detail(
    admin_client: Client,
) -> None:
    obj = PackageRatingFactory()
    path = f"/djangoadmin/repository/packagerating/{obj.pk}/change/"
    resp = admin_client.get(
        path=path,
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200
