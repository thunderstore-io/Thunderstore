from typing import IO, Any, Dict, Optional, TypedDict

from django.conf import settings
from django.core.files import File
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
    url_protocol: str
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
        """
        with TemporarySpooledCopy(content) as tmp_content:
            final_name = super().save(name, content, max_length)

            for storage_mirror in self.mirrors:
                storage_mirror._save(final_name, File(tmp_content, final_name))

        return final_name

    def delete(self, name: str) -> None:
        """
        Delete file from main S3 storage and all mirrors.
        """
        super().delete(name)

        for storage_mirror in self.mirrors:
            storage_mirror.delete(name)
