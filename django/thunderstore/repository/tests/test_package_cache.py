import pytest

from thunderstore.cache.cache import CacheBustCondition


@pytest.mark.django_db
def test_package_cache_not_invalidated_on_download_counter_increase(
    package_version, mocker
):
    mocked_invalidate_cache = mocker.patch(
        "thunderstore.repository.models.package.invalidate_cache"
    )
    package_version._increase_download_counter()
    mocked_invalidate_cache.assert_not_called()


@pytest.mark.django_db
def test_package_cache_is_invalidated_on_version_hidden(package_version, mocker):
    mocked_invalidate_cache = mocker.patch(
        "thunderstore.repository.models.package.invalidate_cache"
    )
    package_version.is_active = False
    package_version.save()
    mocked_invalidate_cache.assert_called_with(CacheBustCondition.any_package_updated)


@pytest.mark.django_db
def test_package_cache_is_invalidated_on_listing_delete(active_package_listing, mocker):
    mocked_invalidate_cache = mocker.patch(
        "thunderstore.community.models.package_listing.invalidate_cache"
    )
    active_package_listing.delete()
    mocked_invalidate_cache.assert_called_with(CacheBustCondition.any_package_updated)
