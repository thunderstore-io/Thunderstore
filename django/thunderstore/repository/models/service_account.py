import ulid2
from django.conf import settings
from django.db import models


class ServiceAccount(models.Model):
    uuid = models.UUIDField(default=ulid2.generate_ulid_as_uuid, primary_key=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name="service_account",
        on_delete=models.CASCADE,
    )
    is_service_account = models.BooleanField(default=False)
    owner = models.ForeignKey(
        "repository.UploaderIdentity",
        related_name="service_accounts",
        on_delete=models.CASCADE,
    )
