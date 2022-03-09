import ulid2
from django.contrib.postgres.fields.citext import CICharField
from django.db import models
from django.db.models import Manager
from django.utils import timezone
from pydantic import BaseModel

from thunderstore.core.mixins import TimestampMixin


class PrimitiveKey(BaseModel):
    key_identifier: str
    key: str
    is_current: bool


class KeyType(models.TextChoices):
    SECP256R1 = "SECP256R1", "SECP256R1"


class KeyProvider(TimestampMixin, models.Model):
    stored_public_keys: "Manager[StoredPublicKey]"
    id = models.UUIDField(
        default=ulid2.generate_ulid_as_uuid, primary_key=True, editable=False
    )
    identifier = CICharField(
        unique=True,
        max_length=64,
    )
    provider_url = models.CharField(max_length=256)
    datetime_last_synced = models.DateTimeField()

    class Meta:
        verbose_name = "key provider"
        verbose_name_plural = "key providers"

    def __str__(self) -> str:
        return (
            f"Provider identifier: {self.identifier} Provider URL: {self.provider_url}"
        )

    def record_update_timestamp(self):
        self.datetime_last_synced = timezone.now()
        self.save()


class StoredPublicKey(TimestampMixin, models.Model):
    id = models.UUIDField(
        default=ulid2.generate_ulid_as_uuid, primary_key=True, editable=False
    )
    provider = models.ForeignKey(
        "ts_github.KeyProvider",
        on_delete=models.CASCADE,
        blank=True,
        related_name="stored_public_keys",
    )
    key_identifier = models.TextField()
    key_type = models.TextField(
        choices=KeyType.choices,
    )
    key = models.TextField()
    is_active = models.BooleanField(
        default=False,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("provider", "key_identifier"),
                name="one_key_identifier_per_provider",
            ),
        ]
        verbose_name = "stored public key"
        verbose_name_plural = "stored public keys"

    def __str__(self) -> str:
        return f"Identifier: {self.key_identifier}"
