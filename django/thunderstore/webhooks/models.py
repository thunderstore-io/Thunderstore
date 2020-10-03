import uuid
import json

import requests
from django.db.models import Q

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
        related_name="webhook_exclusions",
        blank=True,
    )
    require_categories = models.ManyToManyField(
        "community.PackageCategory",
        related_name="webhook_inclusions",
        blank=True,
    )
    allow_nsfw = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    @classmethod
    def get_for_package_release(cls, package):
        categories = package.primary_package_listing.categories.all()
        webhooks = Webhook.objects.exclude(exclude_categories__in=categories).filter(
            Q(webhook_type=WebhookType.mod_release) &
            Q(is_active=True) &
            Q(Q(require_categories=None) | Q(require_categories__in=categories))
        )
        if package.primary_package_listing.has_nsfw_content:
            webhooks = webhooks.exclude(allow_nsfw=False)
        return webhooks

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
