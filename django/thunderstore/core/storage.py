from typing import IO, Any, Dict, Optional, TypedDict

from django.conf import settings
from django.core.cache import cache
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

        Calling .save() closes the file, so use temporary copies for
        mirrors and call the main bucket with the actual file last.
        """

        cache_key = f"cache_mirror_storage_{name}"

        if not cache.add(cache_key, "LOCKED", timeout=5):
            raise Exception("Another save operation is in progress for this file.")

        try:
            for storage_mirror in self.mirrors:
                with TemporarySpooledCopy(content) as tmp_content:
                    storage_mirror.save(name, tmp_content, max_length)

            return super().save(name, content, max_length)
        finally:
            cache.delete(cache_key)

    def delete(self, name: str) -> None:
        """
        Delete file from main S3 storage and all mirrors.
        """
        super().delete(name)

        for storage_mirror in self.mirrors:
            storage_mirror.delete(name)
