import json
from typing import Any, Dict
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.test import APIClient

from thunderstore.community.models import PackageListing
from thunderstore.ts_trending.models import TrendingScore
from thunderstore.ts_trending.permissions import TrendingSharedSecretPermission
from thunderstore.utils.gzip import gzip_compress

SECRET = "ABC123"


@patch.object(TrendingSharedSecretPermission, "SHARED_SECRET", SECRET)
@pytest.mark.django_db
def test_ingest_requires_shared_secret(api_client: APIClient) -> None:
    response = _post(api_client, {}, HTTP_AUTHORIZATION="TS-Secret not-a-secret")

    assert response.status_code == 401


@patch.object(TrendingSharedSecretPermission, "SHARED_SECRET", SECRET)
@pytest.mark.django_db
def test_ingest_stores_gzipped_scores(
    api_client: APIClient,
    active_package_listing: PackageListing,
) -> None:
    payload = _get_payload([[active_package_listing.package.pk, 42.57], [0, 32.1]])

    response = api_client.post(
        reverse("api:experimental:trending.ingest"),
        gzip_compress(json.dumps(payload).encode()),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"TS-Secret {SECRET}",
        HTTP_CONTENT_ENCODING="gzip",
    )

    assert response.status_code == 200
    assert response.data == {"trending": 1, "new-and-trending": 0}
    score = TrendingScore.objects.get()
    assert score.listing == active_package_listing
    assert score.score == 42.57
    assert score.datetime_computed.isoformat() == "2026-11-12T09:00:00+00:00"


@patch.object(TrendingSharedSecretPermission, "SHARED_SECRET", SECRET)
@pytest.mark.django_db
def test_ingest_rejects_invalid_gzip(api_client: APIClient) -> None:
    response = api_client.post(
        reverse("api:experimental:trending.ingest"),
        b"not gzip",
        content_type="application/json",
        HTTP_AUTHORIZATION=f"TS-Secret {SECRET}",
        HTTP_CONTENT_ENCODING="gzip",
    )

    assert response.status_code == 400


@patch.object(TrendingSharedSecretPermission, "SHARED_SECRET", SECRET)
@pytest.mark.django_db
def test_ingest_rejects_stale_push(
    api_client: APIClient,
    active_package_listing: PackageListing,
) -> None:
    TrendingScore.objects.create(
        listing=active_package_listing,
        score=1.5,
        datetime_computed=timezone.now(),
    )

    response = _post(api_client, _get_payload([]))

    assert response.status_code == 409
    assert TrendingScore.objects.get().score == 1.5


@patch.object(TrendingSharedSecretPermission, "SHARED_SECRET", SECRET)
@pytest.mark.django_db
def test_ingest_rejects_empty_push(
    api_client: APIClient,
    active_package_listing: PackageListing,
) -> None:
    _post(api_client, _get_payload([[active_package_listing.package.pk, 42.57]]))

    response = _post(
        api_client,
        {**_get_payload([[0, 32.1]]), "computed_at": "2026-11-12T10:00:00Z"},
    )

    assert response.status_code == 400
    assert TrendingScore.objects.get().score == 42.57


@patch.object(TrendingSharedSecretPermission, "SHARED_SECRET", SECRET)
@pytest.mark.django_db
@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("computed_at", "2999-01-01T00:00:00Z"),
        ("sorts", {"trending": {}}),
        ("sorts", {"trending": {"test": [[1]]}, "new-and-trending": {}}),
        ("sorts", {"trending": {"test": [[1, "nan"]]}, "new-and-trending": {}}),
        ("sorts", {"trending": {"test": ["12"]}, "new-and-trending": {}}),
        ("sorts", {"trending": {"test": [[True, False]]}, "new-and-trending": {}}),
    ),
)
def test_ingest_rejects_invalid_payload(
    api_client: APIClient,
    field: str,
    value: Any,
) -> None:
    response = _post(api_client, {**_get_payload([]), field: value})

    assert response.status_code == 400
    assert field in response.data


def _get_payload(scores: list) -> Dict[str, Any]:
    return {
        "schema_version": 1,
        "computed_at": "2026-11-12T09:00:00Z",
        "sorts": {"trending": {"test": scores}, "new-and-trending": {}},
    }


def _post(api_client: APIClient, payload: Dict[str, Any], **extra: Any) -> Response:
    return api_client.post(
        reverse("api:experimental:trending.ingest"),
        json.dumps(payload),
        content_type="application/json",
        **{"HTTP_AUTHORIZATION": f"TS-Secret {SECRET}", **extra},
    )
