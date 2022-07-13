import pytest
from django.conf import settings
from django.test import Client

from thunderstore.repository.models import PackageVersion


@pytest.mark.django_db
def test_admin_package_version_search(admin_client: Client) -> None:
    resp = admin_client.get(
        path="/djangoadmin/repository/packageversion/?q=asd",
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_package_version_list(admin_client: Client) -> None:
    resp = admin_client.get(
        path="/djangoadmin/repository/packageversion/",
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_package_version_detail(
    package_version: PackageVersion,
    admin_client: Client,
) -> None:
    path = f"/djangoadmin/repository/packageversion/{package_version.pk}/change/"
    resp = admin_client.get(
        path=path,
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200
