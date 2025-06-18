import pytest
from django.conf import settings
from django.test import Client, RequestFactory

from thunderstore.core.factories import UserFactory
from thunderstore.repository.admin.package_version import (
    PackageVersionAdmin,
    approve_version,
    extract_file_list,
    reject_version,
)
from thunderstore.repository.consts import PackageVersionReviewStatus
from thunderstore.repository.factories import PackageVersionFactory
from thunderstore.repository.models import PackageVersion, Team


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


@pytest.mark.django_db
def test_admin_package_version_extract_file_list(
    package_version: PackageVersion,
    mocker,
):
    mocked_task = mocker.patch(
        "thunderstore.repository.admin.package_version.extract_package_version_file_tree.delay"
    )

    extract_file_list(None, None, PackageVersion.objects.all())

    mocked_task.assert_called_once_with(package_version.pk)


@pytest.mark.django_db
def test_admin_package_version_approve_version(team: Team) -> None:
    versions = [PackageVersionFactory() for _ in range(5)]

    request = RequestFactory().get("/")
    request.user = UserFactory()
    request.user.is_superuser = True

    modeladmin = PackageVersionAdmin(PackageVersion, None)
    approve_version(modeladmin, request, PackageVersion.objects.all())

    for entry in versions:
        entry.refresh_from_db()
        assert entry.review_status == PackageVersionReviewStatus.approved


@pytest.mark.django_db
def test_admin_package_version_reject_version(team: Team) -> None:
    versions = [PackageVersionFactory() for _ in range(5)]

    request = RequestFactory().get("/")
    request.user = UserFactory()
    request.user.is_superuser = True

    modeladmin = PackageVersionAdmin(PackageVersion, None)
    reject_version(modeladmin, request, PackageVersion.objects.all())

    for entry in versions:
        entry.refresh_from_db()
        assert entry.review_status == PackageVersionReviewStatus.rejected
