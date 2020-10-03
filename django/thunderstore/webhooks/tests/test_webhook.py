import pytest

from thunderstore.webhooks.models import Webhook


@pytest.mark.django_db
@pytest.mark.parametrize("is_active", (False, True))
def test_webhook_get_for_package_release_is_active(release_webhook, active_package, is_active):
    release_webhook.is_active = is_active
    release_webhook.save(update_fields=("is_active",))
    result = Webhook.get_for_package_release(active_package)
    if is_active:
        assert release_webhook in result
    else:
        assert release_webhook not in result


@pytest.mark.django_db
@pytest.mark.parametrize("allow_nsfw", (False, True))
def test_webhook_get_for_package_release_filter_nsfw(release_webhook, active_package, allow_nsfw):
    release_webhook.allow_nsfw = allow_nsfw
    release_webhook.save(update_fields=("allow_nsfw",))

    listing = active_package.primary_package_listing
    listing.has_nsfw_content = True
    listing.save(update_fields=("has_nsfw_content",))
    listing.refresh_from_db()
    assert listing.has_nsfw_content is True

    result = Webhook.get_for_package_release(active_package)
    if allow_nsfw:
        assert release_webhook in result
    else:
        assert release_webhook not in result


@pytest.mark.django_db
@pytest.mark.parametrize("should_exclude", (False, True))
def test_webhook_get_for_package_release_exclude_categories(release_webhook, active_package, package_category, should_exclude):
    listing = active_package.primary_package_listing
    listing.categories.add(package_category)
    listing.refresh_from_db()
    assert package_category in listing.categories.all()

    if should_exclude:
        release_webhook.exclude_categories.add(package_category)

    result = Webhook.get_for_package_release(active_package)
    if should_exclude:
        assert release_webhook not in result
    else:
        assert release_webhook in result


@pytest.mark.django_db
@pytest.mark.parametrize("should_require", (False, True))
def test_webhook_get_for_package_release_require_categories(release_webhook, active_package, package_category, should_require):
    listing = active_package.primary_package_listing
    assert package_category not in listing.categories.all()

    if should_require:
        release_webhook.require_categories.add(package_category)

    result = Webhook.get_for_package_release(active_package)
    if should_require:
        assert release_webhook not in result
    else:
        assert release_webhook in result
