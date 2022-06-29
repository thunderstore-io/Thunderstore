from contextlib import contextmanager
from tempfile import SpooledTemporaryFile
from typing import BinaryIO, TypedDict

from boto3.s3.transfer import TransferConfig  # type: ignore
from boto3.session import Session  # type: ignore
from django.conf import settings
from django.utils.deconstruct import deconstructible
from mypy_boto3_s3.service_resource import Object, S3ServiceResource
from storages.backends.s3boto3 import S3Boto3Storage  # type: ignore


class S3MirrorConfig(TypedDict):
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_STORAGE_BUCKET_NAME: str
    AWS_S3_ENDPOINT_URL: str
    AWS_S3_REGION_NAME: str


@deconstructible
class MirroredS3Storage(S3Boto3Storage):
    def _save(self, name: str, content: BinaryIO) -> str:
        """
        Upload file to main S3 storage and all mirrors.

        Mimics super()._save() for each mirror without accessing config
        values via self.properties or closing the content file. Finally
        calls parent method to upload to main S3 storage.
        """
        cleaned_name = self._clean_name(name)
        key = self._normalize_name(cleaned_name)
        params = self._get_write_parameters(key, content)
        transfer_config = TransferConfig(use_threads=True)
        zipped_content = None

        if (
            self.gzip
            and params["ContentType"] in self.gzip_content_types
            and "ContentEncoding" not in params
        ):
            zipped_content = self._compress_content(content)
            params["ContentEncoding"] = "gzip"

        for mirror in settings.S3_MIRRORS:
            obj = self._get_mirror_object(mirror, key)

            with TemporarySpooledCopy(zipped_content or content) as tmp:
                obj.upload_fileobj(tmp, ExtraArgs=params, Config=transfer_config)

        # Save to main S3 storage last, as this closes the file.
        return super()._save(name, content)

    def delete(self, name: str) -> None:
        """
        Delete file from main S3 storage and all mirrors.
        """
        super().delete(name)

        key: str = self._normalize_name(self._clean_name(name))

        for mirror in settings.S3_MIRRORS:
            obj = self._get_mirror_object(mirror, key)
            obj.delete()

    def _get_mirror_object(self, mirror_config: S3MirrorConfig, key: str) -> Object:
        """
        Return Object on target mirror.

        Object is "A resource representing an Amazon S3 Object"
        """
        session = Session(
            aws_access_key_id=mirror_config["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=mirror_config["AWS_SECRET_ACCESS_KEY"],
        )
        connection: S3ServiceResource = session.resource(
            "s3",
            region_name=mirror_config["AWS_S3_REGION_NAME"],
            endpoint_url=mirror_config["AWS_S3_ENDPOINT_URL"],
            config=self.config,
        )
        bucket = connection.Bucket(mirror_config["AWS_STORAGE_BUCKET_NAME"])
        return bucket.Object(key)


@contextmanager
def TemporarySpooledCopy(source_file: BinaryIO):
    """
    Context with a temporary copy of the given file.

    This is required because boto automatically closes the file object
    once it's uplaoded to S3, but we need to keep the file open so we
    can upload it into multiple mirrors.

    Inspired by django-storage's S3ManifestStaticStorage.
    """
    try:
        source_file.seek(0)
        temp_file = SpooledTemporaryFile()
        temp_file.write(source_file.read())
        temp_file.seek(0)
        yield temp_file
    finally:
        temp_file.close()
