import gzip
import json
from datetime import timedelta
from typing import Any

import pytest

from thunderstore.community.consts import PackageListingReviewStatus
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
from thunderstore.repository.api.v1.viewsets import _get_prefetched_listing_queryset
from thunderstore.repository.factories import (
    PackageRatingFactory,
    PackageVersionFactory,
)
from thunderstore.repository.models import APIV1ChunkedPackageCache, APIV1PackageCache
from thunderstore.repository.models.cache import get_package_listing_ids


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
def test_api_v1_chunked_package_cache__json_shape_order_and_values(
    community: Community,
) -> None:
    listing = PackageListingFactory(community_=community)
    package = listing.package
    package.versions.all().delete()
    PackageVersionFactory(package=package, version_number="1.0.0", is_active=True)
    PackageVersionFactory(package=package, version_number="2.0.0", is_active=False)
    v15 = PackageVersionFactory(package=package, version_number="1.5.0", is_active=True)
    PackageRatingFactory(package=package)
    PackageRatingFactory(package=package)
    dep = PackageVersionFactory()
    v15.dependencies.add(dep)

    update_api_v1_chunked_package_caches()
    cache = APIV1ChunkedPackageCache.get_latest_for_community(community)
    chunk = json.loads(gzip.decompress(cache.chunks.entries.first().blob.data.read()))

    obj = chunk[0]
    assert list(obj.keys()) == [
        "name",
        "full_name",
        "owner",
        "package_url",
        "donation_link",
        "date_created",
        "date_updated",
        "uuid4",
        "rating_score",
        "is_pinned",
        "is_deprecated",
        "has_nsfw_content",
        "categories",
        "versions",
    ]
    assert list(obj["versions"][0].keys()) == [
        "name",
        "full_name",
        "description",
        "icon",
        "version_number",
        "dependencies",
        "download_url",
        "downloads",
        "date_created",
        "website_url",
        "is_active",
        "uuid4",
        "file_size",
    ]
    assert [v["version_number"] for v in obj["versions"]] == ["1.5.0", "1.0.0"]
    assert obj["rating_score"] == 2
    assert obj["versions"][0]["dependencies"] == [dep.full_version_name]


@pytest.mark.django_db
def test_get_package_listing_ids__returns_ids_for_community() -> None:
    community_a = CommunityFactory()
    community_b = CommunityFactory()
    listing_a = PackageListingFactory(community_=community_a)
    PackageListingFactory(community_=community_b)

    result = list(get_package_listing_ids(community_a))
    ids = [id_ for chunk in result for id_ in chunk]

    assert ids == [listing_a.id]


@pytest.mark.django_db
def test_get_package_listing_ids__does_not_return_ids_for_rejected_packages() -> None:
    community = CommunityFactory()
    PackageListingFactory(
        community_=community, review_status=PackageListingReviewStatus.rejected
    )

    result = list(get_package_listing_ids(community))
    ids = [id_ for chunk in result for id_ in chunk]

    assert ids == []


@pytest.mark.django_db
def test_get_prefetched_listing_queryset__prefetches_versions_and_dependencies() -> None:
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    listing = PackageListingFactory()
    dependency = PackageVersionFactory()
    version = listing.package.versions.get()
    version.dependencies.add(dependency)

    prefetched_listing = list(_get_prefetched_listing_queryset([listing.id]))[0]

    with CaptureQueriesContext(connection) as ctx:
        versions = list(prefetched_listing.package.versions.all())
        dependencies = list(versions[0].dependencies.all())
        dependency_owner = dependencies[0].package.owner.name

    assert len(ctx.captured_queries) == 0
    assert versions[0].is_active is True
    assert dependency_owner == dependency.package.owner.name
