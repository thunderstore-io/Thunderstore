from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage

from thunderstore.utils.makemigrations import StubStorage, is_migrate_check


def get_cache_storage():
    # Required as a placeholder stub for migrations, otherwise Django thinks
    # something keeps changing due to settings being different.
    if is_migrate_check():
        return StubStorage()
    return S3Boto3Storage(
        **{
            "access_key": settings.CACHE_S3_ACCESS_KEY_ID,
            "secret_key": settings.CACHE_S3_SECRET_ACCESS_KEY,
            "file_overwrite": settings.CACHE_S3_FILE_OVERWRITE,
            "object_parameters": settings.CACHE_S3_OBJECT_PARAMETERS,
            "bucket_name": settings.CACHE_S3_STORAGE_BUCKET_NAME,
            "location": settings.CACHE_S3_LOCATION,
            "custom_domain": settings.CACHE_S3_CUSTOM_DOMAIN,
            "secure_urls": settings.CACHE_S3_SECURE_URLS,
            "endpoint_url": settings.CACHE_S3_ENDPOINT_URL,
            "region_name": settings.CACHE_S3_REGION_NAME,
            "default_acl": settings.CACHE_S3_DEFAULT_ACL,
        }
    )


CACHE_STORAGE = get_cache_storage()
