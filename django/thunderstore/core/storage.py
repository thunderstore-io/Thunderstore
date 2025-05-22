from typing import IO, Any, Dict, Optional, TypedDict

from django.conf import settings
from django.utils.deconstruct import deconstructible
from storages.backends.s3boto3 import S3Boto3Storage  # type: ignore

from thunderstore.utils.contexts import TemporarySpooledCopy
from thunderstore.utils.makemigrations import is_migrate_check


# These are required as a placeholder stub for migrations, otherwise Django thinks
# something keeps changing due to settings being different.
def get_storage_class_or_stub(storage_class: str) -> str:
    if is_migrate_check():
        return "thunderstore.utils.makemigrations.StubStorage"
    return storage_class


class S3MirrorConfig(TypedDict):
    access_key: str
    secret_key: str
    region_name: str
    bucket_name: str
    location: str
    custom_domain: str
    endpoint_url: str
    secure_urls: bool
    file_overwrite: bool
    default_acl: str
    object_parameters: Dict


@deconstructible
class MirroredS3Storage(S3Boto3Storage):
    @property
    def mirrors(self):
        for mirror in settings.S3_MIRRORS:
            yield S3Boto3Storage(**mirror)

    def save(
        self, name: str, content: IO[Any], max_length: Optional[int] = None
    ) -> str:
        """
        Upload file to main S3 storage and all mirrors.

        Save file to main storage, use temporary file since .save() closes the file.

        Save file to all mirrors, use file name from main storage since we need
        to store the same file name in all mirrors in case of duplicate or alternate
        file names.

        Lock the process to avoid race conditions.
        """

        from thunderstore.cache.utils import get_cache

        CACHE_LOCK_TIMEOUT = 30
        cache = get_cache("default")
        lock_key = f"mirror_storage_cache_{name}"

        with cache.lock(lock_key, timeout=CACHE_LOCK_TIMEOUT, blocking_timeout=None):
            with TemporarySpooledCopy(content) as tmp_content:
                final_name = super().save(name, tmp_content, max_length)

            for storage_mirror in self.mirrors:
                with TemporarySpooledCopy(content) as tmp_content:
                    storage_mirror.save(final_name, tmp_content, max_length)

            return final_name

    def delete(self, name: str) -> None:
        """
        Delete file from main S3 storage and all mirrors.
        """
        super().delete(name)

        for storage_mirror in self.mirrors:
            storage_mirror.delete(name)
