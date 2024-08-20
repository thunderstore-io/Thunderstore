import gzip
import json
from datetime import timedelta
from random import shuffle
from typing import Any

import pytest

from thunderstore.community.factories import (
    CommunityFactory,
    CommunitySiteFactory,
    PackageListingFactory,
    SiteFactory,
)
from thunderstore.community.models import Community, CommunitySite, PackageListing
from thunderstore.repository.api.v1.tasks import (
    update_api_v1_caches,
    update_api_v1_chunked_package_caches,
)
from thunderstore.repository.models import APIV1ChunkedPackageCache, APIV1PackageCache
from thunderstore.repository.models.cache import get_package_listing_chunk


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


@pytest.mark.django_db
def test_api_v1_chunked_package_cache__builds_index_and_chunks(
    community: Community,
    settings: Any,
) -> None:
    PackageListingFactory(community_=community)
    assert APIV1ChunkedPackageCache.get_latest_for_community(community) is None

    update_api_v1_chunked_package_caches()
    cache = APIV1ChunkedPackageCache.get_latest_for_community(community)
    assert cache is not None
    assert cache.index.data_url.startswith(settings.AWS_S3_ENDPOINT_URL)

    index = APIV1ChunkedPackageCache.get_blob_content(cache.index)
    assert isinstance(index, list)
    assert len(index) == cache.chunks.entries.count()
    assert index[0].startswith(settings.AWS_S3_ENDPOINT_URL)


@pytest.mark.django_db
def test_api_v1_chunked_package_cache__drops_stale_caches() -> None:
    """
    Caches are currently only soft deleted.
    """
    PackageListingFactory()
    assert not APIV1ChunkedPackageCache.objects.exists()

    update_api_v1_chunked_package_caches()
    first_cache = APIV1ChunkedPackageCache.objects.get()
    assert not first_cache.is_deleted

    # Only one cache for the community exists, so it won't be dropped.
    APIV1ChunkedPackageCache.drop_stale_cache()
    assert not first_cache.is_deleted

    # Two caches exists, but neither is beyond the cutoff period.
    update_api_v1_chunked_package_caches()
    APIV1ChunkedPackageCache.drop_stale_cache()
    second_cache = APIV1ChunkedPackageCache.get_latest_for_community(
        first_cache.community,
    )
    assert APIV1ChunkedPackageCache.objects.count() == 2
    assert second_cache
    assert second_cache.pk != first_cache.pk
    assert not first_cache.is_deleted
    assert not second_cache.is_deleted

    # The older cache should be dropped after the cutoff period.
    cutoff = timedelta(hours=APIV1ChunkedPackageCache.CACHE_CUTOFF_HOURS)
    first_cache.created_at = first_cache.created_at - cutoff
    first_cache.save()
    APIV1ChunkedPackageCache.drop_stale_cache()
    first_cache.refresh_from_db()
    second_cache.refresh_from_db()
    assert first_cache.is_deleted
    assert not second_cache.is_deleted

    # The latest cache should not be dropped even if older than the cutoff period.
    second_cache.created_at = second_cache.created_at - cutoff
    second_cache.save()
    APIV1ChunkedPackageCache.drop_stale_cache()
    first_cache.refresh_from_db()
    second_cache.refresh_from_db()
    assert first_cache.is_deleted
    assert not second_cache.is_deleted


@pytest.mark.django_db
@pytest.mark.parametrize("count", (0, 1, 2, 3, 5, 8, 13))
def test_get_package_listing_chunk__retains_received_ordering(count: int) -> None:
    assert not PackageListing.objects.exists()
    for _ in range(count):
        PackageListingFactory()

    ordering = list(PackageListing.objects.all().values_list("id", flat=True))
    shuffle(ordering)
    listings = get_package_listing_chunk(ordering)

    for i, listing in enumerate(listings):
        assert listing.id == ordering[i]
