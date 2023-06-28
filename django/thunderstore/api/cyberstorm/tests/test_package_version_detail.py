from datetime import datetime
from typing import Dict

import pytest
from django.http import Http404, HttpRequest
from django.urls import reverse
from rest_framework.test import APIClient

from thunderstore.api.cyberstorm.views import PackageVersionDetailAPIView
from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.factories import CommunitySiteFactory, PackageListingFactory
from thunderstore.core.factories import UserFactory


@pytest.mark.django_db
def test_api_cyberstorm_package_detail_fields(
    api_client: APIClient,
) -> None:

    site1 = CommunitySiteFactory()
    listing1 = PackageListingFactory(
        community_=site1.community, package_version_kwargs={"downloads": 89235981}
    )
    for x in listing1.package.versions.all():
        assert x.downloads == 89235981

    data = __query_api(
        api_client,
        site1.community.identifier,
        listing1.package.namespace.name,
        listing1.package.name,
        listing1.package.versions.all()[0].version_number,
    )

    assert data["name"] == listing1.package.name
    assert data["namespace"] == listing1.package.namespace.name
    assert data["community"] == listing1.community.identifier
    assert data["short_description"] == listing1.package.versions.all()[0].description
    assert data["image_source"] == listing1.package.versions.all()[0].icon.url
    assert data["download_count"] == listing1.package.versions.all()[0].downloads
    assert data["size"] == listing1.package.versions.all()[0].file_size
    assert data["author"] == listing1.package.owner.name
    assert data["is_pinned"] == listing1.package.is_pinned
    assert data["is_nsfw"] == listing1.has_nsfw_content
    assert data["is_deprecated"] == listing1.package.is_deprecated
    assert data["description"] == listing1.package.versions.all()[0].readme
    assert data["github_link"] == listing1.package.versions.all()[0].website_url
    assert data["donation_link"] == listing1.package.owner.donation_link
    assert (
        datetime.fromisoformat(data["upload_date"].replace("Z", "+00:00"))
        == listing1.package.versions.all()[0].date_created
    )
    assert data["version"] == listing1.package.versions.all()[0].version_number
    assert data["changelog"] == listing1.package.versions.all()[0].changelog
    assert (
        data["dependency_string"]
        == listing1.package.versions.all()[0].full_version_name
    )
    assert data["team"]["name"] == listing1.package.owner.name
    for tm in data["team"]["members"]:
        assert listing1.package.owner.members.filter(
            user__username=tm["user"], role=tm["role"]
        ).exists()


@pytest.mark.django_db
def test_api_cyberstorm_package_detail_can_be_viewed_by_user_failure() -> None:
    pl = PackageListingFactory(review_status=PackageListingReviewStatus.rejected)
    view = PackageVersionDetailAPIView()
    user = UserFactory()
    request = HttpRequest()
    setattr(request, "user", user)
    with pytest.raises(Http404) as e_info:
        view.get(
            request,
            pl.community.identifier,
            pl.package.namespace.name,
            pl.package.name,
            pl.package.versions.all()[0].version_number,
        )
    assert str(e_info.value) == ""


def __query_api(
    client: APIClient,
    community_id: str,
    package_namespace: str,
    package_name: str,
    package_version: str,
    response_status_code=200,
) -> Dict:
    url = reverse(
        "api:cyberstorm:cyberstorm.package.version",
        kwargs={
            "community_id": community_id,
            "package_namespace": package_namespace,
            "package_name": package_name,
            "package_version": package_version,
        },
    )
    response = client.get(f"{url}")
    assert response.status_code == response_status_code
    return response.json()
