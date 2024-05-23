import gzip
from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone
from freezegun.api import FrozenDateTimeFactory
from storages.backends.s3boto3 import S3Boto3Storage

from thunderstore.cache.storage import get_cache_storage
from thunderstore.community.factories import CommunityFactory, PackageListingFactory
from thunderstore.community.models import Community
from thunderstore.repository.models.cache import (
    APIV1ChunkedPackageCache,
    APIV1PackageCache,
)
from thunderstore.storage.models import DataBlob, DataBlobGroup
from thunderstore.utils.makemigrations import StubStorage


@pytest.mark.django_db
def test_api_v1_package_cache_get_latest_for_community_without_community(
    community: Community,
) -> None:
    # Make sure a community is in the DB to ensure a random one isn't returned
    assert community.pk
    assert APIV1PackageCache.get_latest_for_community(community_identifier=None) is None


@pytest.mark.django_db
def test_api_v1_package_cache_get_latest_for_community(settings: Any) -> None:
    settings.DISABLE_TRANSACTION_CHECKS = True
    community_a = CommunityFactory()
    community_b = CommunityFactory()
    assert (
        APIV1PackageCache.get_latest_for_community(
            community_identifier=community_a.identifier
        )
        is None
    )
    assert (
        APIV1PackageCache.get_latest_for_community(
            community_identifier=community_b.identifier
        )
        is None
    )

    APIV1PackageCache.update_for_community(community_a, b"")
    APIV1PackageCache.update_for_community(community_b, b"")
    assert APIV1PackageCache.get_latest_for_community(community_identifier=None) is None
    cache_a = APIV1PackageCache.get_latest_for_community(
        community_identifier=community_a.identifier
    )
    cache_b = APIV1PackageCache.get_latest_for_community(
        community_identifier=community_b.identifier
    )
    assert cache_a.pk != cache_b.pk
    assert cache_a.community == community_a
    assert cache_b.community == community_b

    APIV1PackageCache.update_for_community(community_a, b"")
    cache_a2 = APIV1PackageCache.get_latest_for_community(
        community_identifier=community_a.identifier
    )
    assert cache_a2.pk != cache_a.pk
    cache_b.delete()
    assert (
        APIV1PackageCache.get_latest_for_community(
            community_identifier=community_b.identifier
        )
        is None
    )


@pytest.mark.django_db
def test_api_v1_packge_cache_update_for_community(community: Community) -> None:
    content = b"this is a test message"
    assert (
        APIV1PackageCache.get_latest_for_community(
            community_identifier=community.identifier
        )
        is None
    )
    latest = APIV1PackageCache.update_for_community(community, content=content)
    assert latest.content_type == "application/json"
    assert latest.content_encoding == "gzip"
    assert latest.community.pk == community.pk
    assert (
        APIV1PackageCache.get_latest_for_community(
            community_identifier=community.identifier
        ).pk
        == latest.pk
    )
    with gzip.GzipFile(fileobj=latest.data, mode="r") as f:
        result = f.read()
    assert result == content


@pytest.mark.django_db
def test_api_v1_package_cache_drop_stale_cache(
    freezer: FrozenDateTimeFactory, settings: Any
) -> None:
    settings.DISABLE_TRANSACTION_CHECKS = True
    start = timezone.now()
    community_a = CommunityFactory()
    community_b = CommunityFactory()
    cache_a1 = APIV1PackageCache.update_for_community(community_a, b"")
    cache_b1 = APIV1PackageCache.update_for_community(community_b, b"")
    communityless_cache = APIV1PackageCache.update_for_community(community_a, b"")
    communityless_cache.community = None
    communityless_cache.save()

    # B1 is within 1 hours of B2 so should not be dropped
    # TODO: Use freezegun once https://github.com/spulec/freezegun/issues/331 is fixed
    # freezer.move_to(start + timedelta(minutes=30))
    cache_b2 = APIV1PackageCache.update_for_community(community_b, b"")
    cache_b2.last_modified = start + timedelta(minutes=30)
    cache_b2.save()

    # A1 is over 60 minutes older than A2 and should be dropped
    # TODO: Use freezegun once https://github.com/spulec/freezegun/issues/331 is fixed
    # freezer.move_to(start + timedelta(minutes=61))
    cache_a2 = APIV1PackageCache.update_for_community(community_a, b"")
    cache_a2.last_modified = start + timedelta(minutes=61)
    cache_a2.save()

    assert APIV1PackageCache.objects.filter(pk=communityless_cache.pk).count() == 1
    APIV1PackageCache.drop_stale_cache()
    assert APIV1PackageCache.objects.filter(pk=communityless_cache.pk).count() == 0
    assert APIV1PackageCache.objects.filter(pk=cache_a1.pk).count() == 0
    assert APIV1PackageCache.objects.filter(pk=cache_a2.pk).count() == 1
    assert APIV1PackageCache.objects.filter(pk=cache_b1.pk).count() == 1
    assert APIV1PackageCache.objects.filter(pk=cache_b2.pk).count() == 1


@pytest.mark.django_db
def test_api_v1_package_cache_drop_stale_cache_none(settings: Any) -> None:
    settings.DISABLE_TRANSACTION_CHECKS = True
    CommunityFactory()  # Create a community without a community site
    assert APIV1PackageCache.drop_stale_cache() is None  # Ensure no crash


@pytest.mark.django_db
def test_api_v1_package_cache_delete_file_transactions_disabled(community: Community):
    cache = APIV1PackageCache.update_for_community(community, b"")
    with pytest.raises(RuntimeError, match="Must not be called during a transaction"):
        cache._delete_file()


@pytest.mark.django_db(transaction=True)
def test_api_v1_package_cache_delete_file_transactionless_allowed(community: Community):
    cache = APIV1PackageCache.update_for_community(community, b"")
    cache._delete_file()


@pytest.mark.django_db
def test_api_v1_package_cache_delete_file(community: Community, settings: Any):
    settings.DISABLE_TRANSACTION_CHECKS = True
    cache = APIV1PackageCache.update_for_community(community, b"")
    storage: S3Boto3Storage = cache.data.storage
    assert isinstance(storage, S3Boto3Storage)
    name = cache.data.name
    assert storage.exists(name)
    cache._delete_file()
    assert not storage.exists(name)
    cache.refresh_from_db()
    assert cache.is_deleted is True
    assert bool(cache.data) is False


@pytest.mark.django_db
def test_api_v1_package_cache_delete(community: Community, settings: Any):
    settings.DISABLE_TRANSACTION_CHECKS = True
    cache = APIV1PackageCache.update_for_community(community, b"")
    storage: S3Boto3Storage = cache.data.storage
    assert isinstance(storage, S3Boto3Storage)
    name = cache.data.name
    assert storage.exists(name)
    cache.delete()
    assert not storage.exists(name)


@pytest.mark.django_db
def test_api_v1_package_cache_queryset_delete_disallowed():
    with pytest.raises(NotImplementedError, match="Delete is not supported for"):
        APIV1PackageCache.objects.all().delete()


def test_api_v1_packge_cache_storage_is_stub_during_makemigrations(mocker):
    mocker.patch("sys.argv", ["manage.py", "makemigrations"])
    storage = get_cache_storage()
    assert isinstance(storage, StubStorage)


def test_api_v1_packge_cache_storage_is_s3_during_run(mocker):
    mocker.patch("sys.argv", ["manage.py", "runserver"])
    storage = get_cache_storage()
    assert isinstance(storage, S3Boto3Storage)


@pytest.mark.django_db
def test_api_v1_chunked_package_cache__when_no_cache__get_latest_returns_none(
    community: Community,
) -> None:
    assert not APIV1ChunkedPackageCache.objects.exists()
    assert APIV1ChunkedPackageCache.get_latest_for_community(community) is None


@pytest.mark.django_db
def test_api_v1_chunked_package_cache__when_one_cache__get_latest_returns_it(
    community: Community,
) -> None:
    APIV1ChunkedPackageCache.update_for_community(community)
    assert APIV1ChunkedPackageCache.objects.count() == 1
    assert APIV1ChunkedPackageCache.get_latest_for_community(community) is not None


@pytest.mark.django_db
def test_api_v1_chunked_package_cache__when_many_cache__get_latest_returns_latest(
    community: Community,
) -> None:
    APIV1ChunkedPackageCache.update_for_community(community)
    APIV1ChunkedPackageCache.update_for_community(community)
    APIV1ChunkedPackageCache.update_for_community(community)
    latest = APIV1ChunkedPackageCache.objects.order_by("-created_at").first()
    assert APIV1ChunkedPackageCache.objects.count() == 3
    assert APIV1ChunkedPackageCache.get_latest_for_community(community).pk == latest.pk


@pytest.mark.django_db
def test_api_v1_chunked_package_cache__when_community_has_no_packages__creates_index_and_empty_chunk(
    community: Community,
) -> None:
    assert not community.package_listings.exists()
    assert not APIV1ChunkedPackageCache.objects.filter(community=community).exists()

    APIV1ChunkedPackageCache.update_for_community(community)
    cache = APIV1ChunkedPackageCache.objects.get(community=community)
    index = APIV1ChunkedPackageCache.get_blob_content(cache.index)
    assert isinstance(index, list)
    assert len(index) == 1
    assert isinstance(index[0], str)

    assert cache.chunks.entries.count() == 1
    chunk = APIV1ChunkedPackageCache.get_blob_content(cache.chunks.entries.get().blob)
    assert isinstance(chunk, list)
    assert len(chunk) == 0


@pytest.mark.django_db
def test_api_v1_chunked_package_cache__when_community_has_one_package__creates_proper_chunk(
    community: Community,
) -> None:
    listing = PackageListingFactory(
        community_=community,
        package_version_kwargs={"is_active": True},
    )
    assert community.package_listings.count() == 1

    APIV1ChunkedPackageCache.update_for_community(community)
    cache = APIV1ChunkedPackageCache.objects.get(community=community)
    assert cache.chunks.entries.count() == 1
    chunk = APIV1ChunkedPackageCache.get_blob_content(cache.chunks.entries.get().blob)
    assert isinstance(chunk, list)
    assert len(chunk) == 1
    assert chunk[0]["name"] == listing.package.name
    assert isinstance(chunk[0]["versions"], list)
    assert len(chunk[0]["versions"]) == 1
    assert (
        chunk[0]["versions"][0]["full_name"] == listing.package.latest.full_version_name
    )


# Serialized size of a minimal listing returned by PackageListingFactory.
# Has some padding since the exact size varies a bit based on how many
# packages the test creates and thus how long the package names are.
TEST_PACKAGE_BYTES = 1000


@pytest.mark.django_db
@pytest.mark.parametrize(
    (
        "listing_count",
        "chunk_size_limit",
        "expected_chunk_count",
    ),
    (
        (0, 1, 1),
        (1, 1, 1),
        (2, 1, 2),
        (3, 1, 3),
        (0, TEST_PACKAGE_BYTES, 1),
        (1, TEST_PACKAGE_BYTES, 1),
        (2, TEST_PACKAGE_BYTES, 2),
        (3, TEST_PACKAGE_BYTES, 3),
        (0, TEST_PACKAGE_BYTES * 2, 1),
        (1, TEST_PACKAGE_BYTES * 2, 1),
        (2, TEST_PACKAGE_BYTES * 2, 1),
        (3, TEST_PACKAGE_BYTES * 2, 2),
        (4, TEST_PACKAGE_BYTES * 2, 2),
        (5, TEST_PACKAGE_BYTES * 2, 3),
        (0, TEST_PACKAGE_BYTES * 3, 1),
        (1, TEST_PACKAGE_BYTES * 3, 1),
        (2, TEST_PACKAGE_BYTES * 3, 1),
        (3, TEST_PACKAGE_BYTES * 3, 1),
        (4, TEST_PACKAGE_BYTES * 3, 2),
    ),
)
def test_api_v1_chunked_package_cache__when_multiple_packages__creates_correct_amount_of_chunks(
    community: Community,
    listing_count: int,
    chunk_size_limit: int,
    expected_chunk_count: int,
) -> None:
    for _ in range(listing_count):
        PackageListingFactory(
            community_=community,
            package_version_kwargs={"is_active": True},
        )
    assert community.package_listings.count() == listing_count

    APIV1ChunkedPackageCache.update_for_community(community, chunk_size_limit)
    cache = APIV1ChunkedPackageCache.objects.get(community=community)
    assert cache.chunks.entries.count() == expected_chunk_count

    # Will throw if json.loads fails to parse the data.
    for chunk in cache.chunks.entries.all():
        APIV1ChunkedPackageCache.get_blob_content(chunk.blob)


@pytest.mark.django_db
def test_api_v1_chunked_package_cache__when_no_changes_in_packages__reuses_old_blobs(
    community: Community,
) -> None:
    PackageListingFactory(
        community_=community,
        package_version_kwargs={"is_active": True},
    )
    assert community.package_listings.count() == 1
    assert not APIV1ChunkedPackageCache.objects.exists()
    assert not DataBlob.objects.exists()
    assert not DataBlobGroup.objects.exists()

    APIV1ChunkedPackageCache.update_for_community(community)
    cache1 = APIV1ChunkedPackageCache.get_latest_for_community(community=community)
    APIV1ChunkedPackageCache.update_for_community(community)
    cache2 = APIV1ChunkedPackageCache.get_latest_for_community(community=community)
    assert cache1 is not None
    assert cache2 is not None
    assert APIV1ChunkedPackageCache.objects.count() == 2
    assert cache1.pk != cache2.pk
    assert DataBlob.objects.count() == 2  # One index blob, one chunk blob
    assert cache1.index.pk == cache2.index.pk
    assert cache1.chunks.entries.get().blob.pk == cache2.chunks.entries.get().blob.pk
    assert DataBlobGroup.objects.count() == 2  # While blobs are shared, groups are not
    assert cache1.chunks.pk != cache2.chunks.pk
