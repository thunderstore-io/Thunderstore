import uuid
import json

import requests
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

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
    community_site = models.ForeignKey(
        "community.CommunitySite",
        related_name="webhooks",
        on_delete=models.CASCADE,
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
        base_query = Q(
            Q(webhook_type=WebhookType.mod_release) &
            Q(is_active=True)
        )
        community_query = Q()
        for listing in package.package_listings.all():
            categories = listing.categories.all()
            query = (
                ~Q(exclude_categories__in=categories) &
                Q(Q(require_categories=None) | Q(require_categories__in=categories)) &
                Q(community_site__community=listing.community)
            )
            if listing.has_nsfw_content:
                query &= Q(allow_nsfw=True)
            community_query |= Q(query)

        full_query = base_query & Q(community_query)
        return cls.objects.exclude(~Q(full_query))

    def get_version_release_json(self, version):
        thumbnail_url = version.icon.url
        if not (thumbnail_url.startswith("http://") or thumbnail_url.startswith("https://")):
            thumbnail_url = f"{settings.PROTOCOL}{self.community_site.site.domain}{thumbnail_url}"

        return {
            "embeds": [{
                "title": f"{version.name} v{version.version_number}",
                "type": "rich",
                "description": version.description,
                "url": version.package.get_full_url(self.community_site.site),
                "timestamp": timezone.now().isoformat(),
                "color": 4474879,
                "thumbnail": {
                    "url": thumbnail_url,
                    "width": 256,
                    "height": 256,
                },
                "provider": {
                    "name": self.community_site.site.name,
                    "url": f"{settings.PROTOCOL}{self.community_site.site.domain}/"
                },
                "author": {
                    "name": version.package.owner.name,
                },
                "fields": [{
                    "name": "Total downloads across versions",
                    "value": f"{version.package.downloads}",
                }]
            }]
        }

    def post_package_version_release(self, version):
        self.call_with_json(self.get_version_release_json(version))

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
