from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


def get_abyss_storage():
    return S3Boto3Storage(
        **{
            "access_key": settings.ABYSS_S3_ACCESS_KEY_ID,
            "secret_key": settings.ABYSS_S3_SECRET_ACCESS_KEY,
            "file_overwrite": settings.ABYSS_S3_FILE_OVERWRITE,
            "object_parameters": settings.ABYSS_S3_OBJECT_PARAMETERS,
            "bucket_name": settings.ABYSS_S3_STORAGE_BUCKET_NAME,
            "location": settings.ABYSS_S3_LOCATION,
            "custom_domain": settings.ABYSS_S3_CUSTOM_DOMAIN,
            "secure_urls": settings.ABYSS_S3_SECURE_URLS,
            "endpoint_url": settings.ABYSS_S3_ENDPOINT_URL,
            "region_name": settings.ABYSS_S3_REGION_NAME,
            "default_acl": settings.ABYSS_S3_DEFAULT_ACL,
        }
    )
