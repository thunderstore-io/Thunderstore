import pytest
from django.conf import settings
from freezegun.api import FrozenDateTimeFactory

from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.factories import CommunityFactory
from thunderstore.community.models import PackageListing
from thunderstore.repository.models import Package
from thunderstore.webhooks.models import Webhook, WebhookType


@pytest.mark.django_db
@pytest.mark.parametrize("is_active", (False, True))
def test_webhook_get_for_package_release_is_active(
    release_webhook, active_package_listing, is_active
):
    release_webhook.is_active = is_active
    release_webhook.save(update_fields=("is_active",))
    result = Webhook.get_for_package_release(active_package_listing.package)
    if is_active:
        assert release_webhook in result
    else:
        assert release_webhook not in result


@pytest.mark.django_db
@pytest.mark.parametrize("review_status", PackageListingReviewStatus.options())
@pytest.mark.parametrize("require_approval", (True, False))
def test_webhook_get_for_package_release_review_status(
    release_webhook: Webhook,
    active_package_listing: PackageListing,
    review_status: str,
    require_approval: bool,
):
    active_package_listing.community.require_package_listing_approval = require_approval
    active_package_listing.community.save()
    active_package_listing.review_status = review_status
    active_package_listing.save()

    should_exist = review_status in (
        PackageListingReviewStatus.approved,
        PackageListingReviewStatus.unreviewed,
    )
    if require_approval:
        should_exist = review_status == PackageListingReviewStatus.approved

    result = Webhook.get_for_package_release(active_package_listing.package)
    if should_exist:
        assert release_webhook in result
    else:
        assert release_webhook not in result


@pytest.mark.django_db
@pytest.mark.parametrize("allow_nsfw", (False, True))
def test_webhook_get_for_package_release_filter_nsfw(
    release_webhook, active_package_listing, allow_nsfw
):
    release_webhook.allow_nsfw = allow_nsfw
    release_webhook.save(update_fields=("allow_nsfw",))

    active_package_listing.has_nsfw_content = True
    active_package_listing.save(update_fields=("has_nsfw_content",))
    active_package_listing.refresh_from_db()
    assert active_package_listing.has_nsfw_content is True

    result = Webhook.get_for_package_release(active_package_listing.package)
    if allow_nsfw:
        assert release_webhook in result
    else:
        assert release_webhook not in result


@pytest.mark.django_db
@pytest.mark.parametrize("should_exclude", (False, True))
def test_webhook_get_for_package_release_exclude_categories(
    release_webhook, active_package_listing, package_category, should_exclude
):
    active_package_listing.categories.add(package_category)
    active_package_listing.refresh_from_db()
    assert package_category in active_package_listing.categories.all()

    if should_exclude:
        release_webhook.exclude_categories.add(package_category)

    result = Webhook.get_for_package_release(active_package_listing.package)
    if should_exclude:
        assert release_webhook not in result
    else:
        assert release_webhook in result


@pytest.mark.django_db
@pytest.mark.parametrize("should_require", (False, True))
def test_webhook_get_for_package_release_require_categories(
    release_webhook, active_package_listing, package_category, should_require
):
    assert package_category not in active_package_listing.categories.all()

    if should_require:
        release_webhook.require_categories.add(package_category)

    result = Webhook.get_for_package_release(active_package_listing.package)
    if should_require:
        assert release_webhook not in result
    else:
        assert release_webhook in result


@pytest.mark.django_db
def test_webhook_get_for_package_release_rejected_package(
    release_webhook: Webhook,
    rejected_package_listing: PackageListing,
) -> None:
    # Creating a second webhook just to make sure it doesn't get used,
    # as was the case with TS-1481 (rejected package posted to wrong community)
    Webhook.objects.create(
        name="test",
        webhook_url="https://example.com/",
        webhook_type=WebhookType.mod_release,
        is_active=True,
        community=CommunityFactory(),
    )

    result = Webhook.get_for_package_release(rejected_package_listing.package)
    assert result.count() == 0


@pytest.mark.django_db
def test_webhook_post_package_version_release(
    release_webhook: Webhook,
    active_package_listing: PackageListing,
    freezer: FrozenDateTimeFactory,
    mocker,
) -> None:
    version = active_package_listing.package.latest
    data = release_webhook.get_version_release_json(version)
    assert data["embeds"][0]["url"].startswith(settings.PROTOCOL)
    mocked_call = mocker.patch.object(release_webhook, "call_with_json")
    release_webhook.post_package_version_release(version)
    mocked_call.assert_called_with(data)


@pytest.mark.django_db
def test_webhook_post_package_version_release_no_listing(
    release_webhook: Webhook,
    active_package: Package,
    mocker,
) -> None:
    version = active_package.latest
    result = release_webhook.get_version_release_json(version)
    assert result is None
    mocked_call = mocker.patch.object(release_webhook, "call_with_json")
    release_webhook.post_package_version_release(version)
    mocked_call.assert_not_called()
