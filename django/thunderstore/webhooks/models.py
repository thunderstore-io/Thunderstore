import uuid
import json

import requests

from sentry_sdk import capture_exception

from django.db import models

from thunderstore.core.utils import ChoiceEnum


class WebhookType(ChoiceEnum):
    mod_release = "mod_release"


class Webhook(models.Model):
    name = models.CharField(max_length=256)
    webhook_url = models.CharField(max_length=2083)
    webhook_type = models.CharField(
        max_length=512,
        default=WebhookType.mod_release,
        choices=WebhookType.as_choices(),
    )

    is_active = models.BooleanField(
        default=True,
    )
    date_created = models.DateTimeField(
        auto_now_add=True,
    )
    uuid4 = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

    exclude_categories = models.ManyToManyField(
        "community.PackageCategory",
        related_name="webhooks",
        blank=True,
    )
    allow_nsfw = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def call_with_json(self, webhook_data):
        if not self.is_active:
            return
        try:
            resp = requests.post(
                self.webhook_url, data=json.dumps(webhook_data),
                headers={"Content-Type": "application/json"}
            )
            resp.raise_for_status()
        except Exception as e:
            capture_exception(e)
