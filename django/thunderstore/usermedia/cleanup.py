from thunderstore.core.utils import capture_exception
from thunderstore.usermedia.models import UserMedia
from thunderstore.usermedia.s3_client import get_s3_client
from thunderstore.usermedia.s3_upload import cleanup_expired_upload


def cleanup_expired_uploads():
    client = get_s3_client()
    for entry in UserMedia.objects.expired():
        try:
            cleanup_expired_upload(entry, client)
        except Exception as e:
            capture_exception(e)
