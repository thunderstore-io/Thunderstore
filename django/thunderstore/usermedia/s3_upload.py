from datetime import datetime
from typing import IO, List, Optional, TypedDict, cast

from botocore.exceptions import ClientError
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import TemporaryUploadedFile
from django.db import DEFAULT_DB_ALIAS, connections, transaction
from mypy_boto3_s3 import Client
from mypy_boto3_s3.type_defs import CompletedPartTypeDef

from thunderstore.core.types import UserType
from thunderstore.usermedia.consts import UPLOAD_PART_SIZE
from thunderstore.usermedia.exceptions import (
    InvalidUploadStateException,
    S3BucketNameMissingException,
    S3FileKeyChangedException,
    UploadNotExpiredException,
)
from thunderstore.usermedia.models import UserMedia
from thunderstore.usermedia.models.usermedia import UserMediaStatus


def create_upload(
    client: Client,
    user: Optional[UserType],
    filename: str,
    size: int,
    expiry: Optional[datetime] = None,
) -> UserMedia:
    bucket_name = settings.USERMEDIA_S3_STORAGE_BUCKET_NAME
    if not bucket_name:
        raise S3BucketNameMissingException()

    user_media = UserMedia.create_upload(
        user=user,
        filename=filename,
        size=size,
        expiry=expiry,
    )

    response = client.create_multipart_upload(
        Bucket=bucket_name,
        Key=user_media.key,
        Metadata=user_media.s3_metadata,
    )
    user_media.upload_id = response["UploadId"]
    user_media.status = UserMediaStatus.upload_created
    user_media.save(update_fields=("upload_id", "status"))
    return user_media


UploadPartUrlTypeDef = TypedDict(
    "UploadPartUrlTypeDef",
    {"part_number": int, "url": str, "offset": int, "length": int},
    total=False,
)


def get_signed_upload_urls(
    user: Optional[UserType],
    client: Client,
    user_media: UserMedia,
) -> List[UploadPartUrlTypeDef]:
    bucket_name = settings.USERMEDIA_S3_STORAGE_BUCKET_NAME
    if not bucket_name:
        raise S3BucketNameMissingException()

    if not user_media.can_user_write(user):
        raise PermissionDenied()

    if user_media.status != UserMediaStatus.upload_created:
        raise InvalidUploadStateException(
            current=user_media.status,
            expected=UserMediaStatus.upload_created,
        )

    # Double negative = ceil integer division as opposed to floor
    part_count = -(-user_media.size // UPLOAD_PART_SIZE)

    upload_urls = []
    for part_number in range(1, part_count + 1):
        offset = (part_number - 1) * UPLOAD_PART_SIZE
        length = min(UPLOAD_PART_SIZE, user_media.size - offset)
        upload_urls.append(
            {
                "part_number": part_number,
                "url": client.generate_presigned_url(
                    ClientMethod="upload_part",
                    Params={
                        "Bucket": bucket_name,
                        "Key": user_media.key,
                        "UploadId": user_media.upload_id,
                        "PartNumber": part_number,
                        "ContentLength": length,
                    },
                    ExpiresIn=60 * 60 * 6,
                ),
                "offset": offset,
                "length": length,
            },
        )

    return upload_urls


def finalize_upload(
    user: Optional[UserType],
    client: Client,
    user_media: UserMedia,
    parts: List[CompletedPartTypeDef],
) -> None:
    bucket_name = settings.USERMEDIA_S3_STORAGE_BUCKET_NAME

    if not bucket_name:
        raise S3BucketNameMissingException()

    if not user_media.can_user_write(user):
        raise PermissionDenied()

    if user_media.status != UserMediaStatus.upload_created:
        raise InvalidUploadStateException(
            current=user_media.status,
            expected=UserMediaStatus.upload_created,
        )

    # We need to ensure any potential failure status is recorded to the database
    # appropriately. Easiest way to do this is just to ensure we're not in a
    # transaction, which could end up rolling back our failure status elsewhere
    # from the database. It is not the best solution, but works in preventing
    # accidental bugs due to mishandled transaction usage.
    if (
        connections[DEFAULT_DB_ALIAS].in_atomic_block
        and not settings.DISABLE_TRANSACTION_CHECKS
    ):
        raise RuntimeError("Must not be called during a transaction")

    parts = sorted(parts, key=lambda x: x["PartNumber"])

    try:
        result = client.complete_multipart_upload(
            Bucket=bucket_name,
            Key=user_media.key,
            MultipartUpload={
                "Parts": parts,
            },
            UploadId=user_media.upload_id,
        )

        if result["Key"] != user_media.key:
            raise S3FileKeyChangedException(user_media.key, result["Key"])

        meta = client.head_object(
            Bucket=bucket_name,
            Key=user_media.key,
        )
        user_media.size = meta["ContentLength"]
        user_media.status = UserMediaStatus.upload_complete
        user_media.save(update_fields=("status", "size"))
    except (ClientError, S3FileKeyChangedException) as e:
        user_media.status = UserMediaStatus.upload_error
        user_media.save(update_fields=("status",))
        raise e


def abort_upload(
    user: Optional[UserType], client: Client, user_media: UserMedia
) -> None:
    bucket_name = settings.USERMEDIA_S3_STORAGE_BUCKET_NAME
    if not bucket_name:
        raise S3BucketNameMissingException()

    if not user_media.can_user_write(user):
        raise PermissionDenied()

    valid_states = (
        UserMediaStatus.upload_created,
        UserMediaStatus.upload_aborted,
        UserMediaStatus.upload_error,
    )
    if user_media.status not in valid_states:
        raise InvalidUploadStateException(
            current=user_media.status,
            expected=", ".join(valid_states),
        )

    client.abort_multipart_upload(
        Bucket=bucket_name,
        Key=user_media.key,
        UploadId=user_media.upload_id,
    )
    user_media.status = UserMediaStatus.upload_aborted
    user_media.save(update_fields=("status",))


def download_file(
    user: Optional[UserType],
    client: Client,
    user_media: UserMedia,
) -> TemporaryUploadedFile:
    bucket_name = settings.USERMEDIA_S3_STORAGE_BUCKET_NAME
    if not bucket_name:
        raise S3BucketNameMissingException()

    if not user_media.can_user_write(user):
        raise PermissionDenied()

    if user_media.status != UserMediaStatus.upload_complete:
        raise InvalidUploadStateException(
            current=user_media.status,
            expected=UserMediaStatus.upload_complete,
        )

    fileobj = TemporaryUploadedFile(
        name=user_media.filename,
        content_type=None,
        size=user_media.size,
        charset=None,
    )
    client.download_fileobj(bucket_name, user_media.key, cast(IO, fileobj))
    fileobj.seek(0)
    return fileobj


def ensure_multipart_upload_aborted(
    client: Client, bucket_name: str, user_media: UserMedia
):
    if user_media.upload_id is None:
        # Upload has never existed so just pass
        return
    try:
        client.abort_multipart_upload(
            Bucket=bucket_name,
            Key=user_media.key,
            UploadId=user_media.upload_id,
        )
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", None)
        if code != "NoSuchUpload":  # pragma: no cover
            raise e


def cleanup_expired_upload(user_media: UserMedia, client: Client):
    bucket_name = settings.USERMEDIA_S3_STORAGE_BUCKET_NAME
    if not bucket_name:
        raise S3BucketNameMissingException()

    if not user_media.has_expired:
        raise UploadNotExpiredException()

    # We delete first within a db transaction. If the cleanup operations fail
    # for some reason, the transaction will be rolled back.
    with transaction.atomic():
        user_media.delete()

        if user_media.status not in (
            UserMediaStatus.upload_aborted,
            UserMediaStatus.upload_complete,
        ):
            ensure_multipart_upload_aborted(client, bucket_name, user_media)

        if user_media.status == UserMediaStatus.upload_complete:
            client.delete_object(
                Bucket=bucket_name,
                Key=user_media.key,
            )
