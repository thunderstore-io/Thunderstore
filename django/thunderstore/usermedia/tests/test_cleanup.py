import re
from datetime import timedelta

import pytest
from botocore.exceptions import ClientError
from django.conf import settings
from django.utils import timezone

from thunderstore.usermedia.cleanup import cleanup_expired_uploads
from thunderstore.usermedia.consts import MIN_UPLOAD_SIZE
from thunderstore.usermedia.models import UserMedia
from thunderstore.usermedia.s3_client import get_s3_client
from thunderstore.usermedia.s3_upload import create_upload


@pytest.mark.django_db
def test_usermedia_cleanup() -> None:
    client = get_s3_client()
    expired = [
        create_upload(client, None, "a", MIN_UPLOAD_SIZE, timezone.now()),
        create_upload(
            client, None, "a", MIN_UPLOAD_SIZE, timezone.now() - timedelta(seconds=1)
        ),
        create_upload(
            client, None, "a", MIN_UPLOAD_SIZE, timezone.now() - timedelta(days=400)
        ),
    ]
    active = [
        create_upload(client, None, "a", MIN_UPLOAD_SIZE, None),
        create_upload(
            client, None, "a", MIN_UPLOAD_SIZE, timezone.now() + timedelta(minutes=1)
        ),
        create_upload(
            client, None, "a", MIN_UPLOAD_SIZE, timezone.now() + timedelta(days=400)
        ),
    ]
    cleanup_expired_uploads()
    assert UserMedia.objects.filter(pk__in=[x.pk for x in expired]).count() == 0
    assert UserMedia.objects.filter(pk__in=[x.pk for x in active]).count() == 3
    for entry in expired:
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
                Key=entry.key,
                UploadId=entry.upload_id,
            )
    for entry in active:
        assert (
            client.list_parts(
                Bucket=settings.USERMEDIA_S3_STORAGE_BUCKET_NAME,
                Key=entry.key,
                UploadId=entry.upload_id,
            )
            is not None
        )
