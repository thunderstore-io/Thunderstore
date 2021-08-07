import datetime
import json
from datetime import timedelta
from typing import Any

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from thunderstore.core.factories import UserFactory
from thunderstore.core.types import UserType
from thunderstore.usermedia.consts import MIN_UPLOAD_SIZE
from thunderstore.usermedia.models import UserMedia
from thunderstore.usermedia.models.usermedia import UserMediaStatus
from thunderstore.usermedia.s3_client import get_s3_client
from thunderstore.usermedia.s3_upload import (
    abort_upload,
    create_upload,
    finalize_upload,
    get_signed_upload_urls,
)
from thunderstore.usermedia.tests.utils import upload_usermedia


def stringify_timestamp(timestamp: datetime.datetime) -> str:
    result = timestamp.isoformat()
    if result.endswith("+00:00"):
        result = result[:-6] + "Z"
    return result


@pytest.mark.django_db
def test_api_experimental_usermedia_initiate_upload(
    api_client: APIClient, user: UserType
):
    api_client.force_authenticate(user)
    response = api_client.post(
        reverse("api:experimental:usermedia.initiate-upload"),
        json.dumps(
            {
                "filename": "testfile.zip",
                "file_size_bytes": MIN_UPLOAD_SIZE,
            }
        ),
        content_type="application/json",
    )
    assert response.status_code == 201
    response_data = response.json()
    user_media_data = response_data["user_media"]
    user_media = UserMedia.objects.get(pk=user_media_data["uuid"])
    assert user_media.filename == "testfile.zip"
    assert user_media.size == MIN_UPLOAD_SIZE
    assert user_media.expiry > timezone.now() + timedelta(hours=23)
    assert user_media.expiry < timezone.now() + timedelta(hours=25)
    assert user_media.status == UserMediaStatus.upload_created
    assert user_media_data["expiry"] == stringify_timestamp(user_media.expiry)
    assert user_media_data["status"] == user_media.status
    assert user_media_data["size"] == user_media.size
    assert user_media_data["filename"] == user_media.filename
    parts = response_data["upload_urls"]
    assert len(parts) == 1


@pytest.mark.django_db
def test_api_experimental_usermedia_initiate_upload_no_user(api_client: APIClient):
    response = api_client.post(
        reverse("api:experimental:usermedia.initiate-upload"),
        json.dumps(
            {
                "filename": "testfile.zip",
                "file_size_bytes": MIN_UPLOAD_SIZE,
            }
        ),
        content_type="application/json",
    )
    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication credentials were not provided."
    }


@pytest.mark.django_db(transaction=True)
def test_api_experimental_usermedia_finish_upload(
    api_client: APIClient, user: UserType, settings: Any
):
    settings.USERMEDIA_S3_SIGNING_ENDPOINT_URL = settings.USERMEDIA_S3_ENDPOINT_URL
    api_client.force_authenticate(user)
    response = api_client.post(
        reverse("api:experimental:usermedia.initiate-upload"),
        json.dumps(
            {
                "filename": "testfile.zip",
                "file_size_bytes": MIN_UPLOAD_SIZE,
            }
        ),
        content_type="application/json",
    )
    assert response.status_code == 201
    upload_info = response.json()

    parts = upload_usermedia(
        upload_info["user_media"]["size"],
        upload_info["upload_urls"],
    )

    response = api_client.post(
        reverse(
            "api:experimental:usermedia.finish-upload",
            kwargs=dict(uuid=upload_info["user_media"]["uuid"]),
        ),
        json.dumps({"parts": parts}),
        content_type="application/json",
    )
    assert response.status_code == 200
    finish_info = response.json()

    assert finish_info["uuid"] == upload_info["user_media"]["uuid"]
    usermedia = UserMedia.objects.get(pk=finish_info["uuid"])
    assert usermedia.status == UserMediaStatus.upload_complete


@pytest.mark.django_db
@pytest.mark.parametrize(
    "status",
    [x for x in UserMediaStatus.options() if x != UserMediaStatus.upload_created],
)
def test_api_experimental_usermedia_finish_upload_invalid_state(
    api_client: APIClient,
    user: UserType,
    status: UserMediaStatus,
):
    usermedia = UserMedia.create_upload(user, "test", MIN_UPLOAD_SIZE)
    usermedia.status = status
    usermedia.save()

    api_client.force_authenticate(user)
    response = api_client.post(
        reverse(
            "api:experimental:usermedia.finish-upload", kwargs=dict(uuid=usermedia.uuid)
        ),
        json.dumps(
            {
                "parts": [
                    {
                        "ETag": "1234",
                        "PartNumber": 0,
                    }
                ]
            }
        ),
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.json() == {
        "non_field_errors": [
            f"Invalid upload state. Expected: upload_initiated; found: {status}"
        ]
    }


@pytest.mark.django_db
def test_api_experimental_usermedia_finish_upload_expired(
    api_client: APIClient, user: UserType
):
    usermedia = UserMedia.create_upload(
        user, "test", MIN_UPLOAD_SIZE, expiry=timezone.now() - timedelta(seconds=1)
    )

    api_client.force_authenticate(user)
    response = api_client.post(
        reverse(
            "api:experimental:usermedia.finish-upload", kwargs=dict(uuid=usermedia.uuid)
        ),
        json.dumps(
            {
                "parts": [
                    {
                        "ETag": "1234",
                        "PartNumber": 0,
                    }
                ]
            }
        ),
        content_type="application/json",
    )
    print(response.content)
    assert response.status_code == 404
    assert response.json() == {"detail": "Not found."}


@pytest.mark.django_db
def test_api_experimental_usermedia_finish_upload_wrong_user(
    api_client: APIClient, user: UserType
):
    api_client.force_authenticate(user)
    response = api_client.post(
        reverse("api:experimental:usermedia.initiate-upload"),
        json.dumps(
            {
                "filename": "testfile.zip",
                "file_size_bytes": MIN_UPLOAD_SIZE,
            }
        ),
        content_type="application/json",
    )
    assert response.status_code == 201
    upload_info = response.json()

    api_client.force_authenticate(UserFactory())
    response = api_client.post(
        reverse(
            "api:experimental:usermedia.finish-upload",
            kwargs=dict(uuid=upload_info["user_media"]["uuid"]),
        ),
        json.dumps(
            {
                "parts": [
                    {
                        "ETag": "1234",
                        "PartNumber": 0,
                    }
                ]
            }
        ),
        content_type="application/json",
    )
    assert response.status_code == 403
    assert response.json() == {
        "detail": "You do not have permission to perform this action."
    }


@pytest.mark.django_db
def test_api_experimental_usermedia_finish_upload_no_user(api_client: APIClient):
    usermedia = UserMedia.create_upload(None, "test", MIN_UPLOAD_SIZE)
    response = api_client.post(
        reverse(
            "api:experimental:usermedia.finish-upload", kwargs=dict(uuid=usermedia.uuid)
        ),
        json.dumps(
            {
                "parts": [
                    {
                        "ETag": "1234",
                        "PartNumber": 0,
                    }
                ]
            }
        ),
        content_type="application/json",
    )
    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication credentials were not provided."
    }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("status", [x for x in UserMediaStatus.options()])
def test_api_experimental_usermedia_abort_upload(
    api_client: APIClient,
    user: UserType,
    status: UserMediaStatus,
    settings: Any,
):
    settings.USERMEDIA_S3_SIGNING_ENDPOINT_URL = settings.USERMEDIA_S3_ENDPOINT_URL
    s3_client = get_s3_client()
    usermedia = create_upload(s3_client, user, "test", MIN_UPLOAD_SIZE)

    valid_states = (
        UserMediaStatus.upload_created,
        UserMediaStatus.upload_aborted,
        UserMediaStatus.upload_error,
    )

    if status == UserMediaStatus.upload_complete:
        parts = upload_usermedia(
            size=MIN_UPLOAD_SIZE,
            upload_urls=get_signed_upload_urls(user, s3_client, usermedia),
        )
        finalize_upload(user, s3_client, usermedia, parts)

    if status == UserMediaStatus.upload_aborted:
        abort_upload(user, s3_client, usermedia)

    usermedia.status = status
    usermedia.save()

    api_client.force_authenticate(user)

    response = api_client.post(
        reverse(
            "api:experimental:usermedia.abort-upload", kwargs=dict(uuid=usermedia.uuid)
        ),
        content_type="application/json",
    )
    if status not in valid_states:
        assert response.status_code == 400
        assert response.json() == {
            "non_field_errors": [
                "Invalid upload state. Expected: "
                "upload_initiated, upload_aborted, upload_error; "
                f"found: {status}"
            ]
        }
    elif status == UserMediaStatus.upload_aborted:
        assert response.status_code == 404
        assert response.json() == {"detail": "Upload not found"}
    else:
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["uuid"] == str(usermedia.uuid)
        assert response_data["status"] == UserMediaStatus.upload_aborted
        usermedia.refresh_from_db()
        assert usermedia.status == UserMediaStatus.upload_aborted


@pytest.mark.django_db
def test_api_experimental_usermedia_abort_upload_not_found(
    api_client: APIClient, user: UserType
):
    usermedia = UserMedia.create_upload(user, "test", MIN_UPLOAD_SIZE)
    usermedia.upload_id = "123"
    usermedia.status = UserMediaStatus.upload_created
    usermedia.save()
    api_client.force_authenticate(user)
    response = api_client.post(
        reverse(
            "api:experimental:usermedia.abort-upload", kwargs=dict(uuid=usermedia.uuid)
        ),
        content_type="application/json",
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Upload not found"}


@pytest.mark.django_db
def test_api_experimental_usermedia_abort_upload_expired(
    api_client: APIClient, user: UserType
):
    usermedia = UserMedia.create_upload(
        user, "test", MIN_UPLOAD_SIZE, expiry=timezone.now() - timedelta(seconds=1)
    )
    usermedia.save()

    api_client.force_authenticate(user)
    response = api_client.post(
        reverse(
            "api:experimental:usermedia.abort-upload", kwargs=dict(uuid=usermedia.uuid)
        ),
        content_type="application/json",
    )
    print(response.content)
    assert response.status_code == 404
    assert response.json() == {"detail": "Not found."}


@pytest.mark.django_db
def test_api_experimental_usermedia_abort_upload_wrong_user(
    api_client: APIClient, user: UserType
):
    usermedia = UserMedia.create_upload(user, "test", MIN_UPLOAD_SIZE)
    usermedia.status = UserMediaStatus.upload_created
    usermedia.save()

    api_client.force_authenticate(UserFactory())
    response = api_client.post(
        reverse(
            "api:experimental:usermedia.abort-upload", kwargs=dict(uuid=usermedia.uuid)
        ),
        content_type="application/json",
    )
    assert response.status_code == 403
    assert response.json() == {
        "detail": "You do not have permission to perform this action."
    }


@pytest.mark.django_db
def test_api_experimental_usermedia_abort_upload_no_user(api_client: APIClient):
    usermedia = UserMedia.create_upload(None, "test", MIN_UPLOAD_SIZE)
    response = api_client.post(
        reverse(
            "api:experimental:usermedia.abort-upload", kwargs=dict(uuid=usermedia.uuid)
        ),
        content_type="application/json",
    )
    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication credentials were not provided."
    }
