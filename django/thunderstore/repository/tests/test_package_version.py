from typing import Any, Literal, Union

import pytest
from django.db import IntegrityError

from thunderstore.community.models.package_listing import PackageListing
from thunderstore.repository.factories import PackageVersionFactory
from thunderstore.repository.models import PackageVersion
from thunderstore.repository.package_formats import PackageFormats


@pytest.mark.django_db
def test_get_total_used_disk_space():
    assert PackageVersion.get_total_used_disk_space() == 0
    p1 = PackageVersionFactory.create()
    assert PackageVersion.get_total_used_disk_space() == p1.file_size
    p2 = PackageVersionFactory.create(file_size=212312412)
    assert PackageVersion.get_total_used_disk_space() == p1.file_size + p2.file_size


@pytest.mark.django_db
def test_package_version_manager_active():
    p1 = PackageVersionFactory(is_active=True)
    p2 = PackageVersionFactory(is_active=False)

    active_versions = PackageVersion.objects.active()
    assert p1 in active_versions
    assert p2 not in active_versions


@pytest.mark.django_db
def test_package_version_get_page_url(
    active_package_listing: PackageListing,
) -> None:
    owner_url = active_package_listing.package.latest.get_page_url(
        active_package_listing.community.identifier
    )
    assert (
        owner_url
        == f"/c/test/p/Test_Team/{active_package_listing.package.name}/v/{active_package_listing.package.latest.version_number}/"
    )


@pytest.mark.django_db
def test_package_version_get_owner_url(active_package_listing: PackageListing) -> None:
    owner_url = active_package_listing.package.latest.get_owner_url(
        active_package_listing.community.identifier
    )
    assert owner_url == "/c/test/p/Test_Team/"


@pytest.mark.django_db
@pytest.mark.parametrize("protocol", ("http://", "https://"))
@pytest.mark.parametrize(
    "primary_host", ("primary.example.org", "secondary.example.org")
)
def test_package_version_full_download_url(
    active_package_listing: PackageListing,
    protocol: str,
    primary_host: str,
    settings: Any,
) -> None:
    settings.PRIMARY_HOST = primary_host
    settings.PROTOCOL = protocol
    package = active_package_listing.package
    namespace = package.namespace.name
    version = package.latest
    expected = f"{protocol}{primary_host}/package/download/{namespace}/{package.name}/{version.version_number}/"
    assert version.full_download_url == expected


@pytest.mark.django_db
@pytest.mark.parametrize("format_spec", PackageFormats.values + [None, "invalid"])
def test_package_version_format_spec_constraint(
    package_version: PackageVersion,
    format_spec: Union[PackageFormats, None, Literal["invalid"]],
) -> None:
    package_version.format_spec = format_spec
    should_pass = format_spec != "invalid"
    if should_pass:
        package_version.save()
    else:
        with pytest.raises(
            IntegrityError, match='violates check constraint "valid_package_format"'
        ):
            package_version.save()
