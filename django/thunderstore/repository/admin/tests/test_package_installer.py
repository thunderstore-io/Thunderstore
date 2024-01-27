import pytest
from django.conf import settings
from django.test import Client

from thunderstore.repository.models import PackageInstaller


@pytest.mark.django_db
def test_admin_package_installer_search(admin_client: Client) -> None:
    resp = admin_client.get(
        path="/djangoadmin/repository/packageinstaller/?q=asd",
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_package_installer_list(
    package_installer: PackageInstaller, admin_client: Client
) -> None:
    resp = admin_client.get(
        path="/djangoadmin/repository/packageinstaller/",
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200
    assert package_installer.identifier in resp.content.decode()


@pytest.mark.django_db
def test_admin_package_installer_detail(
    package_installer: PackageInstaller,
    admin_client: Client,
) -> None:
    path = f"/djangoadmin/repository/packageinstaller/{package_installer.pk}/change/"
    resp = admin_client.get(
        path=path,
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200
