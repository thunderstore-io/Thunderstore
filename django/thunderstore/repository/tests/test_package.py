from typing import Any

import pytest

from thunderstore.community.factories import (
    CommunityFactory,
    CommunitySiteFactory,
    SiteFactory,
)
from thunderstore.community.models.package_listing import PackageListing
from thunderstore.repository.models import Package


@pytest.mark.django_db
def test_package_get_owner_url(active_package_listing: PackageListing) -> None:
    owner_url = active_package_listing.package.get_owner_url(
        active_package_listing.community.identifier
    )
    assert owner_url == "/c/test/p/Test_Team/"


@pytest.mark.django_db
def test_package_get_dependants_url(active_package_listing: PackageListing) -> None:
    owner_url = active_package_listing.package.get_dependants_url(
        active_package_listing.community.identifier
    )
    assert (
        owner_url
        == f"/c/test/p/Test_Team/{active_package_listing.package.name}/dependants/"
    )


@pytest.mark.django_db
def test_package_get_page_url(
    active_package_listing: PackageListing,
) -> None:
    owner_url = active_package_listing.package.get_page_url(
        active_package_listing.community.identifier
    )
    assert owner_url == f"/c/test/p/Test_Team/{active_package_listing.package.name}/"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "site_host", ("thunderstore.dev", "test.thunderstore.dev", None)
)
@pytest.mark.parametrize(
    "primary_host", ("thunderstore.io", "stonderthure.io.example.org")
)
def test_package_get_full_url(
    settings: Any,
    site_host: str,
    primary_host: str,
    active_package: Package,
) -> None:
    site = SiteFactory(domain=site_host) if site_host is not None else None
    settings.PRIMARY_HOST = primary_host

    expected_host = site_host if site else primary_host
    expected_url = f"{settings.PROTOCOL}{expected_host}/package/{active_package.namespace.name}/{active_package.name}/"
    assert active_package.get_full_url(site=site) == expected_url
