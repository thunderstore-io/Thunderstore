from hashlib import sha256
from typing import Union, cast
from uuid import UUID

import ulid2
from django.conf import settings
from django.core.cache import caches
from django.core.exceptions import ValidationError
from django.core.files.storage import get_storage_class
from django.core.files.uploadedfile import TemporaryUploadedFile
from django.db import models
from django.db.models import Sum
from django_redis.cache import RedisCache

from thunderstore.core.mixins import TimestampMixin

LEGACYPROFILE_STORAGE_CAP = (
    1024 * 1024 * 1024 * settings.LEGACYPROFILE_MAX_TOTAL_SIZE_GB
)


cache = cast(RedisCache, caches["profiles"])


def get_legacy_profile_file_path(instance: "LegacyProfile", filename: str):
    return f"modpacks/legacyprofile/{instance.id}"


class LegacyProfileManager(models.Manager):
    @staticmethod
    def id_cache(checksum: str) -> str:
        return f"{checksum}.profile_id"

    @staticmethod
    def file_cache(uuid: Union[str, UUID]):
        return f"{uuid}.file_name"

    def get_or_create_from_upload(self, content: TemporaryUploadedFile) -> "UUID":
        if content.size + self.get_total_used_disk_space() > LEGACYPROFILE_STORAGE_CAP:
            raise ValidationError(
                f"The server has reached maximum total storage used, and can't receive new uploads"
            )

        hash = sha256()
        content.seek(0)
        hash.update(content.read())
        hexdigest = hash.hexdigest()

        # TODO: There are more efficient data types available in redis which
        #       can be utilized here. Explore & implement.
        id_cache_key = self.id_cache(hexdigest)

        if profile_id := cache.get(id_cache_key):
            return profile_id

        instance = self.filter(file_size=content.size, file_sha256=hexdigest).first()

        if not instance:
            instance = self.create(
                file=content,
                file_size=content.size,
                file_sha256=hexdigest,
            )

        cache.set_many(
            {
                id_cache_key: instance.id,
                self.file_cache(instance.id): instance.file.name,
            }
        )
        return instance.id

    def get_file_url(self, profile_id: str) -> str:
        cache_key = self.file_cache(profile_id)
        if not (file_name := cache.get(cache_key)):
            file_name = self.get(id=profile_id).file.name
            cache.set(cache_key, file_name)
        return self.model._meta.get_field("file").storage.url(file_name)

    def get_total_used_disk_space(self) -> int:
        return self.aggregate(total=Sum("file_size"))["total"] or 0


class LegacyProfile(TimestampMixin, models.Model):
    objects: "LegacyProfileManager[LegacyProfile]" = LegacyProfileManager()

    id = models.UUIDField(
        default=ulid2.generate_ulid_as_uuid,
        primary_key=True,
        editable=False,
    )
    file = models.FileField(
        upload_to=get_legacy_profile_file_path,
        storage=get_storage_class(settings.MODPACK_FILE_STORAGE)(),
    )
    file_sha256 = models.CharField(
        max_length=512,
        editable=False,
        blank=True,
        null=True,
        db_index=True,
    )
    file_size = models.PositiveBigIntegerField()

    def __str__(self):
        return str(self.id)
