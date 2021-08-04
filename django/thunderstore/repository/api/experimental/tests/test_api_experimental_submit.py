import json
import uuid
from typing import Any, Dict

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from thunderstore.community.models import Community, PackageCategory
from thunderstore.core.factories import UserFactory
from thunderstore.core.types import UserType
from thunderstore.repository.models import (
    UploaderIdentity,
    UploaderIdentityMember,
    UploaderIdentityMemberRole,
)
from thunderstore.repository.package_reference import PackageReference
from thunderstore.usermedia.models import UserMedia


@pytest.mark.django_db
def test_api_experimental_submit_package_success(
    api_client: APIClient,
    user: UserType,
    manifest_v1_data: Dict[str, Any],
    package_category: PackageCategory,
    uploader_identity: UploaderIdentity,
    community: Community,
    manifest_v1_package_upload_id: str,
):
    UploaderIdentityMember.objects.create(
        user=user,
        identity=uploader_identity,
        role=UploaderIdentityMemberRole.owner,
    )

    api_client.force_authenticate(user=user)
    response = api_client.post(
        reverse("api:experimental:submission.submit"),
        json.dumps(
            {
                "upload_uuid": manifest_v1_package_upload_id,
                "author_name": uploader_identity.name,
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
    assert response_data["namespace"] == uploader_identity.name
    assert response_data["name"] == manifest_v1_data["name"]
    assert response_data["version_number"] == manifest_v1_data["version_number"]
    assert PackageReference(uploader_identity.name, "name", "1.0.0").exists is True


@pytest.mark.django_db
def test_api_experimental_submit_package_wrong_user_for_submission(
    api_client: APIClient,
    package_category: PackageCategory,
    uploader_identity: UploaderIdentity,
    community: Community,
    manifest_v1_package_upload_id: str,
):
    user_b = UserFactory()
    assert UserMedia.objects.get(uuid=manifest_v1_package_upload_id).owner != user_b

    UploaderIdentityMember.objects.create(
        user=user_b,
        identity=uploader_identity,
        role=UploaderIdentityMemberRole.owner,
    )
    api_client.force_authenticate(user=user_b)
    response = api_client.post(
        reverse("api:experimental:submission.submit"),
        json.dumps(
            {
                "upload_uuid": manifest_v1_package_upload_id,
                "author_name": uploader_identity.name,
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
    assert PackageReference(uploader_identity.name, "name", "1.0.0").exists is False


@pytest.mark.django_db
def test_api_experimental_submit_package_invalid_upload_id(
    api_client: APIClient,
    user: UserType,
    package_category: PackageCategory,
    uploader_identity: UploaderIdentity,
    community: Community,
):
    UploaderIdentityMember.objects.create(
        user=user,
        identity=uploader_identity,
        role=UploaderIdentityMemberRole.owner,
    )
    upload_id = str(uuid.uuid4())
    api_client.force_authenticate(user=user)
    response = api_client.post(
        reverse("api:experimental:submission.submit"),
        json.dumps(
            {
                "upload_uuid": upload_id,
                "author_name": uploader_identity.name,
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
    assert PackageReference(uploader_identity.name, "name", "1.0.0").exists is False


@pytest.mark.django_db
def test_api_experimental_submit_package_not_signed_in(
    api_client: APIClient,
    user: UserType,
    package_category: PackageCategory,
    uploader_identity: UploaderIdentity,
    community: Community,
    manifest_v1_package_upload_id: str,
):
    UploaderIdentityMember.objects.create(
        user=user,
        identity=uploader_identity,
        role=UploaderIdentityMemberRole.owner,
    )

    api_client.force_authenticate(user=None)
    response = api_client.post(
        reverse("api:experimental:submission.submit"),
        json.dumps(
            {
                "upload_uuid": manifest_v1_package_upload_id,
                "author_name": uploader_identity.name,
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
    assert PackageReference(uploader_identity.name, "name", "1.0.0").exists is False


@pytest.mark.django_db
def test_api_experimental_submit_package_no_team_permission(
    api_client: APIClient,
    user: UserType,
    package_category: PackageCategory,
    uploader_identity: UploaderIdentity,
    community: Community,
    manifest_v1_package_upload_id: str,
):
    api_client.force_authenticate(user=user)
    response = api_client.post(
        reverse("api:experimental:submission.submit"),
        json.dumps(
            {
                "upload_uuid": manifest_v1_package_upload_id,
                "author_name": uploader_identity.name,
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
        "author_name": ["Object with name=Test_Identity does not exist."]
    }
    assert PackageReference(uploader_identity.name, "name", "1.0.0").exists is False


@pytest.mark.django_db
def test_api_experimental_submit_package_invalid_category(
    api_client: APIClient,
    user: UserType,
    package_category: PackageCategory,
    uploader_identity: UploaderIdentity,
    community: Community,
    manifest_v1_package_upload_id: str,
):
    UploaderIdentityMember.objects.create(
        user=user,
        identity=uploader_identity,
        role=UploaderIdentityMemberRole.owner,
    )

    api_client.force_authenticate(user=user)
    category_slug = f"invalid-{package_category.slug}"
    response = api_client.post(
        reverse("api:experimental:submission.submit"),
        json.dumps(
            {
                "upload_uuid": manifest_v1_package_upload_id,
                "author_name": uploader_identity.name,
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
    assert PackageReference(uploader_identity.name, "name", "1.0.0").exists is False
