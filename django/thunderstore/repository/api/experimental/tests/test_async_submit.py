import json
import uuid
from typing import Any, Dict

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from thunderstore.community.factories import CommunityFactory, PackageCategoryFactory
from thunderstore.community.models import Community, PackageCategory, PackageListing
from thunderstore.core.factories import UserFactory
from thunderstore.core.types import UserType
from thunderstore.frontend.api.experimental.serializers.views import (
    CommunitySerializer,
    PackageCategorySerializer,
)
from thunderstore.repository.models import Team, TeamMember, TeamMemberRole
from thunderstore.repository.package_reference import PackageReference
from thunderstore.usermedia.models import UserMedia


def _handle_submit(api_client: APIClient, data: str):
    submission = api_client.post(
        reverse("api:experimental:submission.submit-async"),
        data,
        content_type="application/json",
    )
    if not submission.status_code == 200:
        return submission
    return api_client.get(
        reverse(
            "api:experimental:submission.poll-async",
            kwargs={
                "submission_id": submission.json()["id"],
            },
        ),
        content_type="application/json",
    )


@pytest.mark.django_db(transaction=True)
def test_api_experimental_submit_package_async_success(
    api_client: APIClient,
    user: UserType,
    manifest_v1_data: Dict[str, Any],
    package_category: PackageCategory,
    team: Team,
    community: Community,
    manifest_v1_package_upload_id: str,
):
    com2 = CommunityFactory()
    com3 = CommunityFactory()
    com2_cat1 = PackageCategoryFactory(community=com2)
    com3_cat1 = PackageCategoryFactory(community=com3)
    com3_cat2 = PackageCategoryFactory(community=com3)

    TeamMember.objects.create(
        user=user,
        team=team,
        role=TeamMemberRole.owner,
    )

    api_client.force_authenticate(user=user)
    response = _handle_submit(
        api_client,
        json.dumps(
            {
                "upload_uuid": manifest_v1_package_upload_id,
                "author_name": team.name,
                "categories": [package_category.slug],
                "community_categories": {
                    com2.identifier: [com2_cat1.slug],
                    com3.identifier: [com3_cat1.slug, com3_cat2.slug],
                },
                "communities": [community.identifier, com2.identifier, com3.identifier],
                "has_nsfw_content": True,
            }
        ),
    )
    print(response.content)
    assert response.status_code == 200
    response_data = response.json()["result"]
    version_data = response_data["package_version"]
    assert version_data["namespace"] == team.name
    assert version_data["name"] == manifest_v1_data["name"]
    assert version_data["version_number"] == manifest_v1_data["version_number"]
    assert PackageReference(team.name, "name", "1.0.0").exists is True

    listing_data = response_data["available_communities"]
    assert len(listing_data) == 3
    listing = listing_data[1]
    assert listing["community"] == CommunitySerializer(com2).data
    assert bool(listing["url"])
    assert listing["categories"] == [PackageCategorySerializer(com2_cat1).data]

    package = PackageReference(team.name, "name", "1.0.0").package
    listing = PackageListing.objects.get(community=com2, package=package)
    assert set(listing.categories.values_list("slug", flat=True)) == {com2_cat1.slug}

    listing = PackageListing.objects.get(community=com3, package=package)
    assert set(listing.categories.values_list("slug", flat=True)) == {
        com3_cat1.slug,
        com3_cat2.slug,
    }


@pytest.mark.django_db
def test_api_experimental_submit_package_async_wrong_user_for_submission(
    api_client: APIClient,
    package_category: PackageCategory,
    team: Team,
    community: Community,
    manifest_v1_package_upload_id: str,
):
    user_b = UserFactory()
    assert UserMedia.objects.get(uuid=manifest_v1_package_upload_id).owner != user_b

    TeamMember.objects.create(
        user=user_b,
        team=team,
        role=TeamMemberRole.owner,
    )
    api_client.force_authenticate(user=user_b)
    response = _handle_submit(
        api_client,
        json.dumps(
            {
                "upload_uuid": manifest_v1_package_upload_id,
                "author_name": team.name,
                "categories": [package_category.slug],
                "communities": [community.identifier],
                "has_nsfw_content": True,
            }
        ),
    )
    print(response.content)
    assert response.status_code == 404
    assert response.json() == {
        "detail": "Upload not found or user has insufficient access permissions"
    }
    assert PackageReference(team.name, "name", "1.0.0").exists is False


@pytest.mark.django_db
def test_api_experimental_submit_package_async_invalid_upload_id(
    api_client: APIClient,
    user: UserType,
    package_category: PackageCategory,
    team: Team,
    community: Community,
):
    TeamMember.objects.create(
        user=user,
        team=team,
        role=TeamMemberRole.owner,
    )
    upload_id = str(uuid.uuid4())
    api_client.force_authenticate(user=user)
    response = _handle_submit(
        api_client,
        json.dumps(
            {
                "upload_uuid": upload_id,
                "author_name": team.name,
                "categories": [package_category.slug],
                "communities": [community.identifier],
                "has_nsfw_content": True,
            }
        ),
    )
    print(response.content)
    assert response.status_code == 404
    assert response.json() == {
        "detail": "Upload not found or user has insufficient access permissions"
    }
    assert PackageReference(team.name, "name", "1.0.0").exists is False


@pytest.mark.django_db
def test_api_experimental_submit_package_async_not_signed_in(
    api_client: APIClient,
    user: UserType,
    package_category: PackageCategory,
    team: Team,
    community: Community,
    manifest_v1_package_upload_id: str,
):
    TeamMember.objects.create(
        user=user,
        team=team,
        role=TeamMemberRole.owner,
    )

    api_client.force_authenticate(user=None)
    response = _handle_submit(
        api_client,
        json.dumps(
            {
                "upload_uuid": manifest_v1_package_upload_id,
                "author_name": team.name,
                "categories": [package_category.slug],
                "communities": [community.identifier],
                "has_nsfw_content": True,
            }
        ),
    )
    print(response.content)
    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication credentials were not provided."
    }
    assert PackageReference(team.name, "name", "1.0.0").exists is False


@pytest.mark.django_db
def test_api_experimental_submit_package_async_no_team_permission(
    api_client: APIClient,
    user: UserType,
    package_category: PackageCategory,
    team: Team,
    community: Community,
    manifest_v1_package_upload_id: str,
):
    api_client.force_authenticate(user=user)
    response = _handle_submit(
        api_client,
        json.dumps(
            {
                "upload_uuid": manifest_v1_package_upload_id,
                "author_name": team.name,
                "categories": [package_category.slug],
                "communities": [community.identifier],
                "has_nsfw_content": True,
            }
        ),
    )
    print(response.content)
    assert response.status_code == 400
    assert response.json() == {
        "author_name": ["Object with name=Test_Team does not exist."]
    }
    assert PackageReference(team.name, "name", "1.0.0").exists is False


@pytest.mark.django_db
def test_api_experimental_submit_package_async_invalid_category(
    api_client: APIClient,
    user: UserType,
    package_category: PackageCategory,
    team: Team,
    community: Community,
    manifest_v1_package_upload_id: str,
):
    TeamMember.objects.create(
        user=user,
        team=team,
        role=TeamMemberRole.owner,
    )

    api_client.force_authenticate(user=user)
    category_slug = f"invalid-{package_category.slug}"
    response = _handle_submit(
        api_client,
        json.dumps(
            {
                "upload_uuid": manifest_v1_package_upload_id,
                "author_name": team.name,
                "categories": [category_slug],
                "communities": [community.identifier],
                "has_nsfw_content": True,
            }
        ),
    )
    print(response.content)
    assert response.status_code == 400
    assert response.json() == {"categories": {"0": ["Object not found"]}}
    assert PackageReference(team.name, "name", "1.0.0").exists is False
