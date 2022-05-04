import gzip
from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone
from freezegun.api import FrozenDateTimeFactory
from storages.backends.s3boto3 import S3Boto3Storage

from thunderstore.cache.storage import get_cache_storage
from thunderstore.community.factories import CommunityFactory
from thunderstore.community.models import Community
from thunderstore.repository.models.cache import APIV1PackageCache
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
        cache.delete_file()


@pytest.mark.django_db(transaction=True)
def test_api_v1_package_cache_delete_file_transactionless_allowed(community: Community):
    cache = APIV1PackageCache.update_for_community(community, b"")
    cache.delete_file()


@pytest.mark.django_db
def test_api_v1_package_cache_delete_file(community: Community, settings: Any):
    settings.DISABLE_TRANSACTION_CHECKS = True
    cache = APIV1PackageCache.update_for_community(community, b"")
    storage: S3Boto3Storage = cache.data.storage
    assert isinstance(storage, S3Boto3Storage)
    name = cache.data.name
    assert storage.exists(name)
    cache.delete_file()
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
