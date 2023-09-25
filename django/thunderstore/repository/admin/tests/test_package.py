import pytest
from django.conf import settings
from django.test import Client

from thunderstore.community.models import PackageListing
from thunderstore.repository.admin.package import (
    PackageAdmin,
    deprecate_package,
    undeprecate_package,
)
from thunderstore.repository.models import Package


@pytest.mark.django_db
def test_admin_package_search(admin_client: Client) -> None:
    resp = admin_client.get(
        path="/djangoadmin/repository/package/?q=asd",
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_package_list(admin_client: Client) -> None:
    resp = admin_client.get(
        path="/djangoadmin/repository/package/",
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_package_detail(
    package: Package,
    admin_client: Client,
) -> None:
    path = f"/djangoadmin/repository/package/{package.pk}/change/"
    resp = admin_client.get(
        path=path,
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_package_view_on_site_url(
    active_package_listing: PackageListing,
):
    modeladmin = PackageAdmin(Package, None)
    assert modeladmin.get_view_on_site_url(None) is None
    assert (
        modeladmin.get_view_on_site_url(active_package_listing.package)
        == active_package_listing.get_full_url()
    )


@pytest.mark.django_db
def test_admin_package_action_deprecate_package(
    package: Package,
) -> None:
    # TODO: Call actions through a form post instead
    package.is_deprecated = False
    package.save()
    assert package.is_deprecated is False
    deprecate_package(PackageAdmin, None, Package.objects.all())
    package.refresh_from_db()
    assert package.is_deprecated is True


@pytest.mark.django_db
def test_admin_package_action_undeprecate_package(
    package: Package,
) -> None:
    # TODO: Call actions through a form post instead
    package.is_deprecated = True
    package.save()
    assert package.is_deprecated is True
    undeprecate_package(PackageAdmin, None, Package.objects.all())
    package.refresh_from_db()
    assert package.is_deprecated is False
