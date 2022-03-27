import pickle
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, connections, models
from django.db.models import F, Q
from django.utils import timezone

from thunderstore.cache.storage import CACHE_STORAGE
from thunderstore.core.mixins import TimestampMixin


class DatabaseCache(TimestampMixin, models.Model):
    key = models.CharField(max_length=512, unique=True, db_index=True)
    content = models.BinaryField(blank=True, null=True)
    expires_on = models.DateTimeField(blank=True, null=True)
    hits = models.PositiveIntegerField(default=0)

    @classmethod
    def get(cls, key, default=None):
        query = cls.objects.filter(key=key).exclude(
            Q(expires_on__lte=timezone.now()) & ~Q(expires_on=None)
        )
        result = query.values_list("content", flat=True)
        if result:
            query.update(hits=F("hits") + 1)
            return pickle.loads(result[0])
        return default

    @classmethod
    def set(cls, key, content, timeout=None):
        if timeout:
            expiry = timezone.now() + timedelta(seconds=timeout)
        else:
            expiry = None
        return cls.objects.update_or_create(
            key=key,
            defaults=dict(content=pickle.dumps(content), expires_on=expiry),
        )[0]


def get_package_cache_filepath(_, filename: str) -> str:
    return f"cache/api/v1/package/{filename}"


class S3FileMixinQueryset(models.QuerySet):
    def active(self) -> models.QuerySet:
        return self.exclude(Q(is_deleted=True) | Q(data=None))

    def delete(self):
        # Disallow bulk-delete to ensure deletion happens properly.
        raise NotImplementedError(
            f"Delete is not supported for {self.__class__.__name__}"
        )


class S3FileMixin(models.Model):
    objects: S3FileMixinQueryset["S3FileMixin"] = S3FileMixinQueryset.as_manager()

    data = models.FileField(
        upload_to=get_package_cache_filepath,
        storage=CACHE_STORAGE,
        blank=True,
        null=True,
    )
    content_type = models.TextField()
    content_encoding = models.TextField()
    last_modified = models.DateTimeField()
    is_deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["last_modified"]),
        ]

    def delete_file(self, using: str = None):
        # We need to ensure any potential failure status is recorded to the database
        # appropriately. Easiest way to do this is just to ensure we're not in a
        # transaction, which could end up rolling back our failure status elsewhere
        # from the database. It is not the best solution, but works in preventing
        # accidental bugs due to mishandled transaction usage.
        if (
            connections[using or DEFAULT_DB_ALIAS].in_atomic_block
            and not settings.DISABLE_TRANSACTION_CHECKS
        ):
            raise RuntimeError("Must not be called during a transaction")

        # We use a separate is_deleted flag to ensure transactional safety. It
        # might be possible for a delete to succeed without it being recorded
        # to the database otherwise, as deletion normally happens before
        # a db write.
        self.is_deleted = True
        self.save(update_fields=("is_deleted",))
        self.data.delete()

    def delete(self, using: str = None, **kwargs: Any):
        self.delete_file(using=using)
        super().delete(using=using, **kwargs)
