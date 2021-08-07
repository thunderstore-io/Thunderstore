import os
import re
from datetime import timedelta
from typing import Any, List

import pytest
import requests
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone
from mypy_boto3_s3.type_defs import CompletedPartTypeDef

from thunderstore.core.factories import UserFactory
from thunderstore.usermedia.consts import MIN_UPLOAD_SIZE, UPLOAD_PART_SIZE
from thunderstore.usermedia.exceptions import (
    InvalidUploadStateException,
    S3BucketNameMissingException,
    UploadNotExpiredException,
)
from thunderstore.usermedia.models.usermedia import UserMedia, UserMediaStatus
from thunderstore.usermedia.s3_client import get_s3_client
from thunderstore.usermedia.s3_upload import (
    abort_upload,
    cleanup_expired_upload,
    create_upload,
    download_file,
    finalize_upload,
    get_signed_upload_urls,
)


@pytest.mark.django_db
@pytest.mark.parametrize("with_user", (False, True))
def test_s3_create_upload(with_user: bool) -> None:
    client = get_s3_client()
    user = UserFactory() if with_user else None
    upload = create_upload(
        client=client,
        user=user,
        filename="testfile",
        size=100,
    )
    upload.refresh_from_db()
    assert upload.upload_id
    assert upload.status == UserMediaStatus.upload_created


@pytest.mark.django_db(transaction=True)
def test_s3_create_upload_no_bucket_configured(settings: Any) -> None:
    client = get_s3_client()
    usermedia = UserMedia.create_upload(None, "testfile", 100)
    settings.USERMEDIA_S3_STORAGE_BUCKET_NAME = None
    with pytest.raises(S3BucketNameMissingException):
        create_upload(
            client=client,
            user=None,
            filename="testfile",
            size=100,
        )


@pytest.mark.django_db
@pytest.mark.parametrize("with_user", (False, True))
def test_s3_get_signed_upload_urls(with_user: bool, settings: Any) -> None:
    signing_endpoint = "http://test-endpoint.localhost"
    settings.USERMEDIA_S3_SIGNING_ENDPOINT_URL = signing_endpoint
    client = get_s3_client()
    user = UserFactory() if with_user else None

    expected_upload_parts = 2
    upload_size = UPLOAD_PART_SIZE + 200

    upload = create_upload(
        client=client,
        user=user,
        filename="testfile",
        size=upload_size,
    )
    upload_urls = get_signed_upload_urls(
        user=user,
        client=get_s3_client(for_signing=True),
        user_media=upload,
    )

    assert len(upload_urls) == expected_upload_parts
    for part_number, part in enumerate(upload_urls, 1):
        assert part["part_number"] == part_number
        assert part["url"].startswith(signing_endpoint)
        assert part["offset"] == (UPLOAD_PART_SIZE if part_number == 2 else 0)
        assert part["length"] == (UPLOAD_PART_SIZE if part_number == 1 else 200)


@pytest.mark.django_db
def test_s3_get_signed_upload_urls_wrong_user() -> None:
    client = get_s3_client()
    user_a = UserFactory()
    user_b = UserFactory()

    upload = create_upload(
        client=client,
        user=user_a,
        filename="testfile",
        size=100,
    )
    with pytest.raises(PermissionDenied):
        get_signed_upload_urls(
            user=user_b,
            client=client,
            user_media=upload,
        )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "status",
    [x for x in UserMediaStatus.options() if x != UserMediaStatus.upload_created],
)
def test_s3_get_signed_upload_urls_wrong_upload_status(status: UserMediaStatus) -> None:
    client = get_s3_client()
    usermedia = UserMedia.create_upload(None, "testfile", 100)
    usermedia.status = status

    with pytest.raises(
        InvalidUploadStateException,
        match=f"Invalid upload state. Expected: {UserMediaStatus.upload_created}; found: {status}",
    ):
        get_signed_upload_urls(
            user=None,
            client=client,
            user_media=usermedia,
        )


@pytest.mark.django_db(transaction=True)
def test_s3_get_signed_upload_urls_no_bucket_configured(settings: Any) -> None:
    client = get_s3_client()
    usermedia = UserMedia.create_upload(None, "testfile", 100)
    settings.USERMEDIA_S3_STORAGE_BUCKET_NAME = None
    with pytest.raises(S3BucketNameMissingException):
        get_signed_upload_urls(user=None, client=client, user_media=usermedia)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("with_user", (False, True))
@pytest.mark.parametrize("upload_size", (100, UPLOAD_PART_SIZE * 2 + 50))
def test_s3_finalize_upload(with_user: bool, upload_size: int) -> None:
    client = get_s3_client()
    user = UserFactory() if with_user else None

    upload = create_upload(
        client=client,
        user=user,
        filename="testfile",
        size=upload_size,
    )
    upload_urls = get_signed_upload_urls(
        user=user,
        client=client,
        user_media=upload,
    )

    full_upload = bytearray(os.urandom(upload_size))
    upload_parts: List[CompletedPartTypeDef] = []
    for part in upload_urls:
        response = requests.put(
            url=part["url"], data=full_upload[part["offset"] :][: part["length"]]
        )
        response.raise_for_status()
        upload_parts.append(
            {
                "ETag": response.headers.get("ETag"),
                "PartNumber": part["part_number"],
            }
        )

    finalize_upload(user, client, upload, upload_parts)
    upload.refresh_from_db()

    assert upload.status == UserMediaStatus.upload_complete
    assert upload.size == upload_size


@pytest.mark.django_db(transaction=True)
def test_s3_finalize_upload_wrong_upload_key() -> None:
    client = get_s3_client()
    upload_size = MIN_UPLOAD_SIZE
    upload = create_upload(
        client=client,
        user=None,
        filename="testfile",
        size=upload_size,
    )
    upload_urls = get_signed_upload_urls(
        user=None,
        client=client,
        user_media=upload,
    )

    full_upload = bytearray(os.urandom(upload_size))
    upload_parts: List[CompletedPartTypeDef] = []
    for part in upload_urls:
        response = requests.put(
            url=part["url"], data=full_upload[part["offset"] :][: part["length"]]
        )
        response.raise_for_status()
        upload_parts.append(
            {
                "ETag": response.headers.get("ETag"),
                "PartNumber": part["part_number"],
            }
        )

    upload.key = upload.key + "test"
    upload.save(update_fields=("key",))

    with pytest.raises(ClientError):
        finalize_upload(None, client, upload, upload_parts)

    upload.refresh_from_db()
    assert upload.status == UserMediaStatus.upload_error


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    "status",
    [x for x in UserMediaStatus.options() if x != UserMediaStatus.upload_created],
)
def test_s3_finalize_upload_wrong_upload_status(status: UserMediaStatus) -> None:
    client = get_s3_client()

    usermedia = UserMedia.create_upload(None, "testfile", 100)
    usermedia.status = status

    with pytest.raises(
        InvalidUploadStateException,
        match=f"Invalid upload state. Expected: {UserMediaStatus.upload_created}; found: {status}",
    ):
        finalize_upload(None, client, usermedia, [])


@pytest.mark.django_db(transaction=True)
def test_s3_finalize_upload_wrong_user() -> None:
    client = get_s3_client()
    user_a = UserFactory()
    user_b = UserFactory()

    upload = create_upload(
        client=client,
        user=user_a,
        filename="testfile",
        size=100,
    )
    with pytest.raises(PermissionDenied):
        finalize_upload(user_b, client, upload, [])


@pytest.mark.django_db(transaction=True)
def test_s3_finalize_upload_no_bucket_configured(settings: Any) -> None:
    client = get_s3_client()
    usermedia = UserMedia.create_upload(None, "testfile", 100)
    settings.USERMEDIA_S3_STORAGE_BUCKET_NAME = None
    with pytest.raises(S3BucketNameMissingException):
        finalize_upload(None, client, usermedia, [])


@pytest.mark.django_db(transaction=True)
def test_s3_finalize_upload_within_transaction_should_fail() -> None:
    client = get_s3_client()
    usermedia = UserMedia.create_upload(None, "testfile", 100)
    usermedia.status = UserMediaStatus.upload_created
    usermedia.save()
    with transaction.atomic():
        with pytest.raises(
            RuntimeError, match="Must not be called during a transaction"
        ):
            finalize_upload(None, client, usermedia, [])


@pytest.mark.django_db
@pytest.mark.parametrize("with_user", (False, True))
def test_s3_abort_upload(with_user: bool) -> None:
    client = get_s3_client()
    user = UserFactory() if with_user else None
    upload = create_upload(
        client=client,
        user=user,
        filename="testfile",
        size=100,
    )
    abort_upload(user, client, upload)
    upload.refresh_from_db()
    assert upload.status == UserMediaStatus.upload_aborted


@pytest.mark.django_db
def test_s3_abort_upload_no_bucket_configured(settings: Any) -> None:
    client = get_s3_client()
    usermedia = UserMedia.create_upload(None, "testfile", 100)
    settings.USERMEDIA_S3_STORAGE_BUCKET_NAME = None
    with pytest.raises(S3BucketNameMissingException):
        abort_upload(None, client, usermedia)


@pytest.mark.django_db
def test_s3_abort_upload_wrong_user() -> None:
    client = get_s3_client()
    user_a = UserFactory()
    user_b = UserFactory()

    upload = create_upload(
        client=client,
        user=user_a,
        filename="testfile",
        size=100,
    )
    with pytest.raises(PermissionDenied):
        abort_upload(
            user=user_b,
            client=client,
            user_media=upload,
        )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "status",
    [
        x
        for x in UserMediaStatus.options()
        if x
        not in (
            UserMediaStatus.upload_created,
            UserMediaStatus.upload_aborted,
            UserMediaStatus.upload_error,
        )
    ],
)
def test_s3_abort_upload_wrong_upload_status(status: UserMediaStatus) -> None:
    client = get_s3_client()
    usermedia = UserMedia.create_upload(None, "testfile", 100)
    usermedia.status = status

    valid_states = (
        UserMediaStatus.upload_created,
        UserMediaStatus.upload_aborted,
        UserMediaStatus.upload_error,
    )
    expected = ", ".join(valid_states)
    with pytest.raises(
        InvalidUploadStateException,
        match=f"Invalid upload state. Expected: {expected}; found: {status}",
    ):
        abort_upload(
            user=None,
            client=client,
            user_media=usermedia,
        )


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("with_user", (False, True))
@pytest.mark.parametrize("upload_size", (100, UPLOAD_PART_SIZE + 50))
def test_s3_download_file(with_user: bool, upload_size: int) -> None:
    client = get_s3_client()
    user = UserFactory() if with_user else None

    upload = create_upload(
        client=client,
        user=user,
        filename="testfile",
        size=upload_size,
    )
    upload_urls = get_signed_upload_urls(
        user=user,
        client=client,
        user_media=upload,
    )

    upload_data = bytearray(os.urandom(upload_size))
    upload_parts: List[CompletedPartTypeDef] = []
    for part in upload_urls:
        response = requests.put(
            url=part["url"], data=upload_data[part["offset"] :][: part["length"]]
        )
        response.raise_for_status()
        upload_parts.append(
            {
                "ETag": response.headers.get("ETag"),
                "PartNumber": part["part_number"],
            }
        )

    finalize_upload(user, client, upload, upload_parts)
    upload.refresh_from_db()

    file = download_file(user, client, upload)
    assert file.read() == bytes(upload_data)


@pytest.mark.django_db
def test_s3_download_file_no_bucket_configured(settings: Any) -> None:
    client = get_s3_client()
    usermedia = UserMedia.create_upload(None, "testfile", 100)
    settings.USERMEDIA_S3_STORAGE_BUCKET_NAME = None
    with pytest.raises(S3BucketNameMissingException):
        download_file(None, client, usermedia)


@pytest.mark.django_db
def test_s3_download_file_wrong_user() -> None:
    client = get_s3_client()
    user_a = UserFactory()
    user_b = UserFactory()

    upload = create_upload(
        client=client,
        user=user_a,
        filename="testfile",
        size=100,
    )
    with pytest.raises(PermissionDenied):
        download_file(
            user=user_b,
            client=client,
            user_media=upload,
        )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "status",
    [x for x in UserMediaStatus.options() if x != UserMediaStatus.upload_complete],
)
def test_s3_download_file_wrong_upload_status(status: UserMediaStatus) -> None:
    client = get_s3_client()

    usermedia = UserMedia.create_upload(None, "testfile", 100)
    usermedia.status = status

    with pytest.raises(
        InvalidUploadStateException,
        match=f"Invalid upload state. Expected: {UserMediaStatus.upload_complete}; found: {status}",
    ):
        download_file(None, client, usermedia)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    "status",
    [x for x in UserMediaStatus.options()],
)
def test_s3_cleanup_expired_upload(status: UserMediaStatus) -> None:
    client = get_s3_client()
    upload_size = MIN_UPLOAD_SIZE
    upload = create_upload(
        client=client,
        user=None,
        filename="testfile",
        size=upload_size,
    )

    if status == UserMediaStatus.upload_complete:
        upload_urls = get_signed_upload_urls(
            user=None,
            client=client,
            user_media=upload,
        )
        full_upload = bytearray(os.urandom(upload_size))
        upload_parts: List[CompletedPartTypeDef] = []
        for part in upload_urls:
            response = requests.put(
                url=part["url"], data=full_upload[part["offset"] :][: part["length"]]
            )
            response.raise_for_status()
            upload_parts.append(
                {
                    "ETag": response.headers.get("ETag"),
                    "PartNumber": part["part_number"],
                }
            )

        finalize_upload(None, client, upload, upload_parts)
        upload.refresh_from_db()

    if status == UserMediaStatus.upload_aborted:
        abort_upload(None, client, upload)
        upload.refresh_from_db()
        assert upload.status == status

    upload.expiry = timezone.now() - timedelta(minutes=1)
    upload.status = status
    upload.save()

    if status == UserMediaStatus.upload_complete:
        assert (
            client.head_object(
                Bucket=settings.USERMEDIA_S3_STORAGE_BUCKET_NAME,
                Key=upload.key,
            )["ContentLength"]
            == MIN_UPLOAD_SIZE
        )
    elif status == UserMediaStatus.upload_aborted:
        with pytest.raises(
            ClientError,
            match=re.escape(
                "An error occurred (NoSuchUpload) when calling the ListParts "
                "operation: The specified multipart upload does not exist. The "
                "upload ID may be invalid, or the upload may have been aborted "
                "or completed."
            ),
        ):
            client.list_parts(
                Bucket=settings.USERMEDIA_S3_STORAGE_BUCKET_NAME,
                Key=upload.key,
                UploadId=upload.upload_id,
            )
    else:
        assert (
            client.list_parts(
                Bucket=settings.USERMEDIA_S3_STORAGE_BUCKET_NAME,
                Key=upload.key,
                UploadId=upload.upload_id,
            )
            is not None
        )

    cleanup_expired_upload(upload, client)
    assert UserMedia.objects.filter(pk=upload.pk).count() == 0
    with pytest.raises(
        ClientError,
        match=re.escape(
            "An error occurred (404) when calling the HeadObject operation: Not Found"
        ),
    ):
        client.head_object(
            Bucket=settings.USERMEDIA_S3_STORAGE_BUCKET_NAME,
            Key=upload.key,
        )


@pytest.mark.django_db
def test_s3_cleanup_expired_upload_no_bucket_configured() -> None:
    client = get_s3_client()
    usermedia = UserMedia.create_upload(
        user=None,
        filename="testfile",
        size=100,
        expiry=timezone.now() - timedelta(minutes=1),
    )
    settings.USERMEDIA_S3_STORAGE_BUCKET_NAME = None
    with pytest.raises(S3BucketNameMissingException):
        cleanup_expired_upload(usermedia, client)


@pytest.mark.django_db
def test_s3_cleanup_expired_upload_not_expired() -> None:
    client = get_s3_client()
    usermedia = UserMedia.create_upload(
        user=None,
        filename="testfile",
        size=100,
        expiry=timezone.now() + timedelta(minutes=10),
    )
    with pytest.raises(UploadNotExpiredException):
        cleanup_expired_upload(usermedia, client)
