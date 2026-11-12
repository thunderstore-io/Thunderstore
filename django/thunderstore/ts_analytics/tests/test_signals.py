import json
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from thunderstore.community.models import PackageCategory, PackageListing
from thunderstore.ts_analytics.kafka import KafkaTopic


@pytest.fixture
def mock_send_kafka_message():
    with patch("thunderstore.ts_analytics.signals.send_kafka_message") as mock:
        yield mock


def _get_listing_events(mock_send_kafka_message) -> List[Dict[str, Any]]:
    return [
        json.loads(call.kwargs["payload_string"])
        for call in mock_send_kafka_message.delay.call_args_list
        if call.kwargs["topic"] == KafkaTopic.M_PACKAGE_LISTING_UPDATE_V1
    ]


@pytest.mark.django_db
@pytest.mark.parametrize("reverse", (False, True))
def test_package_listing_category_change_emits_event(
    reverse: bool,
    active_package_listing: PackageListing,
    package_category: PackageCategory,
    mock_send_kafka_message,
    django_capture_on_commit_callbacks,
):
    old_datetime_updated = active_package_listing.datetime_updated

    with django_capture_on_commit_callbacks(execute=True):
        if reverse:
            package_category.packages.add(active_package_listing)
        else:
            active_package_listing.categories.set([package_category])

    events = _get_listing_events(mock_send_kafka_message)
    assert len(events) == 1
    assert events[0]["id"] == active_package_listing.pk
    assert events[0]["categories__slug"] == [package_category.slug]

    active_package_listing.refresh_from_db()
    assert active_package_listing.datetime_updated > old_datetime_updated


@pytest.mark.django_db
def test_package_listing_category_noop_emits_nothing(
    active_package_listing: PackageListing,
    package_category: PackageCategory,
    mock_send_kafka_message,
    django_capture_on_commit_callbacks,
):
    active_package_listing.categories.set([package_category])

    with django_capture_on_commit_callbacks(execute=True):
        active_package_listing.categories.add(package_category)

    assert _get_listing_events(mock_send_kafka_message) == []
