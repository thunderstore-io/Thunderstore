from datetime import datetime
from typing import List, Optional, TypedDict

from django.conf import settings
from django.core.exceptions import PermissionDenied
from mypy_boto3_s3 import Client
from mypy_boto3_s3.type_defs import CompletedPartTypeDef

from thunderstore.core.types import UserType
from thunderstore.usermedia.exceptions import S3BucketNameMissingException
from thunderstore.usermedia.models import UserMedia
from thunderstore.usermedia.models.usermedia import UserMediaStatus


def create_upload(
    client: Client, user: UserType, expiry: Optional[datetime] = None
) -> UserMedia:
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    if not bucket_name:
        raise S3BucketNameMissingException()

    user_media = UserMedia.objects.create(
        status=UserMediaStatus.initial,
        owner=user,
        prefix=settings.AWS_LOCATION,
        expiry=expiry,
    )

    response = client.create_multipart_upload(
        Bucket=bucket_name,
        Key=user_media.file_key,
        Metadata=user_media.s3_metadata,
    )
    user_media.upload_id = response["UploadId"]
    user_media.status = UserMediaStatus.upload_created
    user_media.save(update_fields=("upload_id", "status"))
    return user_media


UploadPartUrlTypeDef = TypedDict(
    "UploadPartUrlTypeDef", {"part_number": int, "url": str}, total=False
)


def get_signed_upload_urls(
    user: UserType, client: Client, user_media: UserMedia, part_count: int
) -> List[UploadPartUrlTypeDef]:
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    if not bucket_name:
        raise S3BucketNameMissingException()

    if not user_media.can_user_write(user):
        raise PermissionDenied()

    upload_urls = []
    for part_number in range(1, part_count + 1):
        upload_urls.append(
            {
                "part_number": part_number,
                "url": client.generate_presigned_url(
                    ClientMethod="upload_part",
                    Params={
                        "Bucket": bucket_name,
                        "Key": user_media.file_key,
                        "UploadId": user_media.upload_id,
                        "PartNumber": part_number,
                    },
                    ExpiresIn=60 * 60 * 6,
                ),
            }
        )

    return upload_urls


def finalize_upload(
    user: UserType,
    client: Client,
    user_media: UserMedia,
    parts: List[CompletedPartTypeDef],
):
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    if not bucket_name:
        raise S3BucketNameMissingException()

    if not user_media.can_user_write(user):
        raise PermissionDenied()

    client.complete_multipart_upload(
        Bucket=bucket_name,
        Key=user_media.file_key,
        MultipartUpload={
            "Parts": parts,
        },
        UploadId=user_media.upload_id,
    )
    user_media.status = UserMediaStatus.upload_complete
    user_media.save(update_fields=("status",))


# TODO: Implement
# We should implement abort_upload to abort uploads by user action, or just
# to clean up organically interrupted uploads. If uploads aren't aborted,
# they will remain on the storage backend indefinitely. See
# https://docs.aws.amazon.com/AmazonS3/latest/API/API_AbortMultipartUpload.html
def abort_upload():
    pass


# TODO: Implement
# Might be needed to properly clean up interrupted or aborted uploads
def list_upload_parts():
    pass
