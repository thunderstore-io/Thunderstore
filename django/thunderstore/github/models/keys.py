from django.contrib.postgres.fields.citext import CICharField
from django.db import models
from django.db.models import Manager

from thunderstore.core.utils import ChoiceEnum


class KeyType(ChoiceEnum):
    SECP256R1 = "SECP256R1"


class KeyProvider(models.Model):
    stored_public_keys: "Manager[StoredPublicKey]"
    name = CICharField(
        primary_key=True,
        max_length=64,
    )
    provider_url = models.CharField(max_length=256)
    last_update_time = models.DateTimeField()

    class Meta:
        verbose_name = "key provider"
        verbose_name_plural = "key providers"

    def __str__(self) -> str:
        return f"Name: {self.name} Provider URL: {self.provider_url}"


class StoredPublicKey(models.Model):
    provider = models.ForeignKey(
        "github.KeyProvider",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="provider",
    )
    key_identifier = models.CharField(
        max_length=512,
    )
    key_type = models.CharField(
        max_length=32,
        choices=KeyType.as_choices(),
    )
    key = models.CharField(
        max_length=512,
    )
    is_active = models.BooleanField(
        default=False,
    )

    class Meta:
        verbose_name = "stored public key"
        verbose_name_plural = "stored public keys"

    def __str__(self) -> str:
        return f"Identifier: {self.key_identifier} Key Type: {self.key_type} Active: {self.is_active} Key: {self.key}"
