import gzip
import json
import time
from io import BytesIO
from typing import Optional

import pytest
from django.conf import settings
from django.utils.http import http_date
from rest_framework.renderers import JSONRenderer
from rest_framework.test import APIClient

from thunderstore.community.models import CommunitySite, PackageListing
from thunderstore.core.factories import UserFactory
from thunderstore.repository.api.v1.tasks import update_api_v1_caches
from thunderstore.repository.api.v1.viewsets import PACKAGE_SERIALIZER
from thunderstore.repository.models.cache import APIV1PackageCache


@pytest.mark.django_db
@pytest.mark.parametrize("old_urls", (False, True))
def test_api_v1_package_list(
    api_client: APIClient,
    community_site: CommunitySite,
    active_package_listing: PackageListing,
    old_urls: str,
) -> None:
    active_package_listing.package.owner.donation_link = "https://example.org/"
    active_package_listing.package.owner.save()
    if old_urls:
        response = api_client.get("/api/v1/package/")
    else:
        response = api_client.get(
            f"/c/{community_site.community.identifier}/api/v1/package/"
        )
    assert response.status_code == 503

    assert (
        APIV1PackageCache.get_latest_for_community(active_package_listing.community)
        is None
    )
    update_api_v1_caches()
    cache = APIV1PackageCache.get_latest_for_community(active_package_listing.community)
    assert cache is not None

    # Should get a full response
    if old_urls:
        response = api_client.get("/api/v1/package/")
    else:
        response = api_client.get(
            f"/c/{community_site.community.identifier}/api/v1/package/"
        )
    assert response.status_code == 200

    # The response is gzipped
    content = BytesIO(response.content)
    with gzip.GzipFile(fileobj=content, mode="r") as f:
        result = json.loads(f.read())

    assert len(result) == 1
    assert result[0]["name"] == active_package_listing.package.name
    assert result[0]["full_name"] == active_package_listing.package.full_package_name
    assert result[0]["donation_link"] == "https://example.org/"
    last_modified = response["Last-Modified"]
    assert last_modified == http_date(int(cache.last_modified.timestamp()))
    assert response["Content-Type"] == cache.content_type
    assert response["Content-Encoding"] == cache.content_encoding

    # Should get a 304 since Last-Modified matches
    if old_urls:
        response = api_client.get(
            path="/api/v1/package/",
            HTTP_IF_MODIFIED_SINCE=last_modified,
        )
    else:
        response = api_client.get(
            path=f"/c/{community_site.community.identifier}/api/v1/package/",
            HTTP_IF_MODIFIED_SINCE=last_modified,
        )
    assert response.status_code == 304

    # We need to sleep at least 0.5 seconds to ensure differing timestamp
    # TODO: Use freezegun or similar instead of sleeping
    # TODO: Use ETag instead of just timestmap
    time.sleep(1)
    update_api_v1_caches()
    new_cache = APIV1PackageCache.get_latest_for_community(
        active_package_listing.community
    )
    assert new_cache != cache
    assert new_cache.last_modified > cache.last_modified

    # Should get a 200 since cache was regenerated
    if old_urls:
        response = api_client.get(
            path="/api/v1/package/",
            HTTP_IF_MODIFIED_SINCE=last_modified,
        )
    else:
        response = api_client.get(
            path=f"/c/{community_site.community.identifier}/api/v1/package/",
            HTTP_IF_MODIFIED_SINCE=last_modified,
        )
    assert response.status_code == 200
    assert response["Last-Modified"] != last_modified
    assert response["Last-Modified"] == http_date(
        int(new_cache.last_modified.timestamp())
    )
    assert len(result) == 1
    assert result[0]["name"] == active_package_listing.package.name
    assert result[0]["full_name"] == active_package_listing.package.full_package_name
    assert result[0]["donation_link"] == "https://example.org/"
    assert result[0]["package_url"].startswith(
        f"{settings.PROTOCOL}{community_site.site.domain}"
    )
    assert result[0]["versions"][0]["download_url"].startswith(
        f"{settings.PROTOCOL}{community_site.site.domain}"
    )


@pytest.mark.django_db
@pytest.mark.parametrize("old_urls", (False, True))
def test_api_v1_package_detail(
    api_client: APIClient,
    community_site: CommunitySite,
    active_package_listing: PackageListing,
    old_urls: str,
) -> None:
    if old_urls:
        response = api_client.get(
            f"/api/v1/package/{active_package_listing.package.uuid4}/",
        )
    else:
        response = api_client.get(
            f"/c/{community_site.community.identifier}/api/v1/package/{active_package_listing.package.uuid4}/",
        )
    assert community_site.community == active_package_listing.community
    assert response.status_code == 200
    result = response.json()
    assert result == json.loads(
        JSONRenderer().render(
            PACKAGE_SERIALIZER(
                instance=active_package_listing,
                context={
                    "community_site": community_site,
                },
            ).data
        )
    )
    assert result["package_url"].startswith(
        f"{settings.PROTOCOL}{community_site.site.domain}"
    )
    assert result["versions"][0]["download_url"].startswith(
        f"{settings.PROTOCOL}{community_site.site.domain}"
    )


@pytest.mark.django_db
@pytest.mark.parametrize("old_urls", (False, True))
def test_api_v1_rate_package(
    api_client: APIClient,
    community_site: CommunitySite,
    active_package_listing: PackageListing,
    old_urls: str,
) -> None:
    uuid = active_package_listing.package.uuid4
    user = UserFactory.create()
    api_client.force_authenticate(user)
    response = api_client.post(
        f"/api/v1/package/{uuid}/rate/",
        json.dumps({"target_state": "rated"}),
        content_type="application/json",
    )
    if old_urls:
        response = api_client.post(
            f"/api/v1/package/{uuid}/rate/",
            json.dumps({"target_state": "rated"}),
            content_type="application/json",
        )
    else:
        response = api_client.post(
            f"/c/{community_site.community.identifier}/api/v1/package/{uuid}/rate/",
            json.dumps({"target_state": "rated"}),
            content_type="application/json",
        )
    assert response.status_code == 200
    result = response.json()
    assert result["state"] == "rated"
    assert result["score"] == 1

    response = api_client.post(
        f"/api/v1/package/{uuid}/rate/",
        json.dumps({"target_state": "unrated"}),
        content_type="application/json",
    )
    assert response.status_code == 200
    result = response.json()
    assert result["state"] == "unrated"
    assert result["score"] == 0


@pytest.mark.django_db
@pytest.mark.parametrize("old_urls", (False, True))
def test_api_v1_rate_package_permission_denied(
    api_client: APIClient,
    community_site: CommunitySite,
    active_package_listing: PackageListing,
    old_urls: str,
) -> None:
    uuid = active_package_listing.package.uuid4
    if old_urls:
        response = api_client.post(
            f"/api/v1/package/{uuid}/rate/",
            json.dumps({"target_state": "rated"}),
            content_type="application/json",
        )
    else:
        response = api_client.post(
            f"/c/{community_site.community.identifier}/api/v1/package/{uuid}/rate/",
            json.dumps({"target_state": "rated"}),
            content_type="application/json",
        )
    assert response.status_code == 403
    assert response.json()["detail"] == "Authentication credentials were not provided."


@pytest.mark.django_db
@pytest.mark.parametrize(
    "donation_link, should_exist",
    (
        (None, False),
        ("https://example.org/", True),
    ),
)
def test_api_v1_package_listing_serializer_donation_link_omission(
    api_client: APIClient,
    active_package_listing: PackageListing,
    donation_link: Optional[str],
    should_exist: bool,
) -> None:
    active_package_listing.package.owner.donation_link = donation_link
    active_package_listing.package.owner.save()
    update_api_v1_caches()
    response = api_client.get("/api/v1/package/")
    assert response.status_code == 200

    # The response is gzipped
    content = BytesIO(response.content)
    with gzip.GzipFile(fileobj=content, mode="r") as f:
        result = json.loads(f.read())

    assert len(result) == 1
    assert result[0]["name"] == active_package_listing.package.name
    assert result[0]["full_name"] == active_package_listing.package.full_package_name
    if should_exist:
        assert "donation_link" in result[0]
        assert result[0]["donation_link"] == donation_link
    else:
        assert "donation_link" not in result[0]
