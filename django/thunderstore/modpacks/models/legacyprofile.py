from hashlib import sha256

import ulid2
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import get_storage_class
from django.core.files.uploadedfile import TemporaryUploadedFile
from django.db import models
from django.db.models import Sum

from thunderstore.core.mixins import TimestampMixin

LEGACYPROFILE_STORAGE_CAP = (
    1024 * 1024 * 1024 * settings.LEGACYPROFILE_MAX_TOTAL_SIZE_GB
)


def get_legacy_profile_file_path(instance: "LegacyProfile", filename: str):
    return f"modpacks/legacyprofile/{instance.id}"


class LegacyProfileManager(models.Manager):
    def get_or_create_from_upload(
        self, content: TemporaryUploadedFile
    ) -> "LegacyProfile":
        if content.size + self.get_total_used_disk_space() > LEGACYPROFILE_STORAGE_CAP:
            raise ValidationError(
                f"The server has reached maximum total storage used, and can't receive new uploads"
            )

        hash = sha256()
        content.seek(0)
        hash.update(content.read())
        hexdigest = hash.hexdigest()

        if existing := self.filter(
            file_size=content.size, file_sha256=hexdigest
        ).first():
            return existing

        return self.create(
            file=content,
            file_size=content.size,
            file_sha256=hexdigest,
        )

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
        max_length=512, editable=False, blank=True, null=True
    )
    file_size = models.PositiveBigIntegerField()

    def __str__(self):
        return str(self.id)
