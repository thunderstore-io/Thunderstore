from binascii import hexlify
from hashlib import sha256
from typing import Optional

from django.conf import settings
from django.core.files import File
from django.db import models, transaction
from django.db.models import Manager, Q
from ipfs_cid import cid_sha256_unwrap_digest, cid_sha256_wrap_digest

from thunderstore.core.mixins import SafeDeleteMixin


def get_ipfs_file_path(instance, _) -> str:
    return f"ipfs/{hexlify(instance.sha256_digest)}"


class IPFSObjectQuerySet(models.QuerySet):
    def active(self) -> models.QuerySet:
        return self.exclude(Q(is_deleted=True) | Q(data=None) | Q(is_active=False))

    def get_active_by_cid(self, cid: str) -> Optional["IPFSObject"]:
        return (
            self.active()
            .filter(
                ipfs_object__sha256_digest=cid_sha256_unwrap_digest(cid),
            )
            .first()
        )

    @transaction.atomic
    def get_or_create_for_file(self, file: File) -> ("IPFSObject", bool):
        hash = sha256()
        hash.update(file)
        digest = hash.digest()
        if existing := self.filter(sha256_digest=digest).first():
            if existing.is_deleted or existing.data:
                existing.is_active = True
                existing.save(update_fields=("is_active",))
            return (existing, False)

        instance = super().create(
            data=file,
            data_size=file.size,
            sha256_digest=digest,
        )
        return (instance, True)

    def create(self):
        raise NotImplementedError(
            f"Manual creation of {self.__class__.__name__} is disallowed. "
            "Use get_or_create_for_file instead."
        )

    def delete(self):
        # Disallow bulk-delete to ensure deletion happens properly.
        raise NotImplementedError(
            f"Delete is not supported for {self.__class__.__name__}"
        )


class IPFSObject(SafeDeleteMixin):
    objects: Manager["IPFSObject"] = IPFSObjectQuerySet.as_manager()

    data = models.FileField(
        upload_to=get_ipfs_file_path,
        storage=settings.IPFS_FILE_STORAGE,
        blank=True,
        null=True,
    )
    data_size = models.fields.PositiveBigIntegerField()
    sha256_digest = models.BinaryField(
        max_length=32,
        db_index=True,
        unique=True,
    )
    is_active = models.BooleanField(default=True)
    datetime_created = models.DateTimeField(auto_now_add=True)

    @property
    def ifps_cid(self):
        return cid_sha256_wrap_digest(self.sha256_digest)

    def safe_delete(self):
        self.data.delete()


class IPFSObjectRelationMixin(models.Model):
    ipfs_object = models.ForeignKey(
        "ipfs.IPFSObject",
        related_name="related_%(app_label)s_%(class)s",
        on_delete=models.PROTECT,
    )

    @classmethod
    def get_by_cid(cls, cid: str) -> Optional[IPFSObject]:
        return cls.objects.filter(
            ipfs_object__sha256_digest=cid_sha256_unwrap_digest(cid),
        ).first()

    class Meta:
        abstract = True
