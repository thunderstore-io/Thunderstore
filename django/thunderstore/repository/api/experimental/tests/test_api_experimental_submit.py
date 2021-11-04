import json
import uuid
from typing import Any, Dict

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from thunderstore.community.api.experimental.serializers import (
    CommunitySerializer,
    PackageCategorySerializer,
)
from thunderstore.community.models import Community, PackageCategory
from thunderstore.core.factories import UserFactory
from thunderstore.core.types import UserType
from thunderstore.repository.models import Team, TeamMember, TeamMemberRole
from thunderstore.repository.package_reference import PackageReference
from thunderstore.usermedia.models import UserMedia


@pytest.mark.django_db
def test_api_experimental_submit_package_success(
    api_client: APIClient,
    user: UserType,
    manifest_v1_data: Dict[str, Any],
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
    response = api_client.post(
        reverse("api:experimental:submission.submit"),
        json.dumps(
            {
                "upload_uuid": manifest_v1_package_upload_id,
                "author_name": team.name,
                "categories": [package_category.slug],
                "communities": [community.identifier],
                "has_nsfw_content": True,
            }
        ),
        content_type="application/json",
    )
    print(response.content)
    assert response.status_code == 200
    response_data = response.json()
    version_data = response_data["package_version"]
    assert version_data["namespace"] == team.name
    assert version_data["name"] == manifest_v1_data["name"]
    assert version_data["version_number"] == manifest_v1_data["version_number"]
    assert PackageReference(team.name, "name", "1.0.0").exists is True

    listing_data = response_data["available_communities"]
    assert len(listing_data) == 1
    listing = listing_data[0]
    assert listing["community"] == CommunitySerializer(community).data
    assert bool(listing["url"])
    assert listing["categories"] == [PackageCategorySerializer(package_category).data]


@pytest.mark.django_db
def test_api_experimental_submit_package_wrong_user_for_submission(
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
    response = api_client.post(
        reverse("api:experimental:submission.submit"),
        json.dumps(
            {
                "upload_uuid": manifest_v1_package_upload_id,
                "author_name": team.name,
                "categories": [package_category.slug],
                "communities": [community.identifier],
                "has_nsfw_content": True,
            }
        ),
        content_type="application/json",
    )
    print(response.content)
    assert response.status_code == 404
    assert response.json() == {
        "detail": "Upload not found or user has insufficient access permissions"
    }
    assert PackageReference(team.name, "name", "1.0.0").exists is False


@pytest.mark.django_db
def test_api_experimental_submit_package_invalid_upload_id(
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
    response = api_client.post(
        reverse("api:experimental:submission.submit"),
        json.dumps(
            {
                "upload_uuid": upload_id,
                "author_name": team.name,
                "categories": [package_category.slug],
                "communities": [community.identifier],
                "has_nsfw_content": True,
            }
        ),
        content_type="application/json",
    )
    print(response.content)
    assert response.status_code == 404
    assert response.json() == {
        "detail": "Upload not found or user has insufficient access permissions"
    }
    assert PackageReference(team.name, "name", "1.0.0").exists is False


@pytest.mark.django_db
def test_api_experimental_submit_package_not_signed_in(
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
    response = api_client.post(
        reverse("api:experimental:submission.submit"),
        json.dumps(
            {
                "upload_uuid": manifest_v1_package_upload_id,
                "author_name": team.name,
                "categories": [package_category.slug],
                "communities": [community.identifier],
                "has_nsfw_content": True,
            }
        ),
        content_type="application/json",
    )
    print(response.content)
    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication credentials were not provided."
    }
    assert PackageReference(team.name, "name", "1.0.0").exists is False


@pytest.mark.django_db
def test_api_experimental_submit_package_no_team_permission(
    api_client: APIClient,
    user: UserType,
    package_category: PackageCategory,
    team: Team,
    community: Community,
    manifest_v1_package_upload_id: str,
):
    api_client.force_authenticate(user=user)
    response = api_client.post(
        reverse("api:experimental:submission.submit"),
        json.dumps(
            {
                "upload_uuid": manifest_v1_package_upload_id,
                "author_name": team.name,
                "categories": [package_category.slug],
                "communities": [community.identifier],
                "has_nsfw_content": True,
            }
        ),
        content_type="application/json",
    )
    print(response.content)
    assert response.status_code == 400
    assert response.json() == {
        "author_name": ["Object with name=Test_Team does not exist."]
    }
    assert PackageReference(team.name, "name", "1.0.0").exists is False


@pytest.mark.django_db
def test_api_experimental_submit_package_invalid_category(
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
    response = api_client.post(
        reverse("api:experimental:submission.submit"),
        json.dumps(
            {
                "upload_uuid": manifest_v1_package_upload_id,
                "author_name": team.name,
                "categories": [category_slug],
                "communities": [community.identifier],
                "has_nsfw_content": True,
            }
        ),
        content_type="application/json",
    )
    print(response.content)
    assert response.status_code == 400
    assert response.json() == {"categories": {"0": ["Object not found"]}}
    assert PackageReference(team.name, "name", "1.0.0").exists is False
