import gzip
import json
from typing import Any

import pytest

from thunderstore.community.factories import (
    CommunityFactory,
    CommunitySiteFactory,
    PackageListingFactory,
    SiteFactory,
)
from thunderstore.community.models import Community, CommunitySite, PackageListing
from thunderstore.repository.api.v1.tasks import update_api_v1_caches
from thunderstore.repository.models import APIV1PackageCache


@pytest.mark.django_db
@pytest.mark.parametrize("create_site", (False, True))
def test_api_v1_cache_building_package_url(
    community: Community,
    active_package_listing: PackageListing,
    create_site: bool,
    settings: Any,
):
    primary_domain = "primary.example.org"
    settings.PRIMARY_HOST = primary_domain
    site_domain = "community.example.org"

    if create_site:
        CommunitySiteFactory(site=SiteFactory(domain=site_domain), community=community)

    assert CommunitySite.objects.filter(community=community).count() == int(create_site)
    assert APIV1PackageCache.get_latest_for_community(community.identifier) is None
    update_api_v1_caches()
    cache = APIV1PackageCache.get_latest_for_community(community.identifier)
    assert cache is not None

    with gzip.GzipFile(fileobj=cache.data, mode="r") as f:
        result = json.loads(f.read())

    domain = site_domain if create_site else primary_domain
    prefix = "/package" if create_site else f"/c/{community.identifier}/p"
    path = f"/{active_package_listing.package.namespace.name}/{active_package_listing.package.name}/"
    assert result[0]["package_url"] == f"{settings.PROTOCOL}{domain}{prefix}{path}"


@pytest.mark.django_db
@pytest.mark.parametrize(
    (
        "protocol",
        "primary_domain",
        "site_domain",
        "community_identifier",
        "expected_prefix",
    ),
    (
        (
            "http://",
            "thunderstore.dev",
            "thunderstore.dev",
            "riskofrain2",
            "http://thunderstore.dev/package/",
        ),
        (
            "http://",
            "thunderstore.dev",
            "ror2.thunderstore.dev",
            "riskofrain2",
            "http://ror2.thunderstore.dev/package/",
        ),
        (
            "https://",
            "thunderstore.dev",
            "ror2.thunderstore.dev",
            "riskofrain2",
            "https://ror2.thunderstore.dev/package/",
        ),
        (
            "https://",
            "thunderstore.dev",
            None,
            "riskofrain2",
            "https://thunderstore.dev/c/riskofrain2/p/",
        ),
        (
            "https://",
            "example.org",
            None,
            "riskofrain2",
            "https://example.org/c/riskofrain2/p/",
        ),
        (
            "https://",
            "example.org",
            "thunderstore.dev",
            "riskofrain2",
            "https://thunderstore.dev/package/",
        ),
        (
            "https://",
            "example.org",
            "thunderstore.dev",
            "valheim",
            "https://thunderstore.dev/package/",
        ),
        (
            "https://",
            "example.org",
            None,
            "valheim",
            "https://example.org/c/valheim/p/",
        ),
    ),
)
def test_api_v1_cache_building_package_url_simple(
    protocol: str,
    primary_domain: str,
    site_domain: str,
    community_identifier: str,
    expected_prefix: str,
    settings: Any,
) -> None:
    settings.PRIMARY_HOST = primary_domain
    settings.PROTOCOL = protocol
    community = CommunityFactory(identifier=community_identifier)
    PackageListingFactory(community_=community)
    if site_domain:
        CommunitySiteFactory(site=SiteFactory(domain=site_domain), community=community)

    assert CommunitySite.objects.filter(community=community).count() == int(
        bool(site_domain)
    )
    assert APIV1PackageCache.get_latest_for_community(community.identifier) is None
    update_api_v1_caches()
    cache = APIV1PackageCache.get_latest_for_community(community.identifier)
    assert cache is not None

    with gzip.GzipFile(fileobj=cache.data, mode="r") as f:
        result = json.loads(f.read())
    assert result[0]["package_url"].startswith(expected_prefix)
