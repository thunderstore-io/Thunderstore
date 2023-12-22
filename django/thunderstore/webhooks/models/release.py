import json
import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
from sentry_sdk import capture_exception

from thunderstore.core.tasks import celery_post
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
    community = models.ForeignKey(
        "community.Community",
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
        base_query = Q(Q(webhook_type=WebhookType.mod_release) & Q(is_active=True))
        community_query = Q()
        communities = []
        for listing in package.community_listings.all():
            if listing.review_status not in listing.community.valid_review_statuses:
                continue
            categories = listing.categories.all()
            query = (
                ~Q(exclude_categories__in=categories)
                & Q(Q(require_categories=None) | Q(require_categories__in=categories))
                & Q(community=listing.community)
            )
            if listing.has_nsfw_content:
                query &= Q(allow_nsfw=True)
            community_query |= Q(query)
            communities.append(listing.community)

        full_query = base_query & Q(community_query) & Q(community__in=communities)
        return cls.objects.exclude(~Q(full_query))

    def get_version_release_json(self, version):
        listing = version.package.get_package_listing(self.community)
        if not listing:
            return None

        thumbnail_url = version.icon.url
        if not (
            thumbnail_url.startswith("http://") or thumbnail_url.startswith("https://")
        ):
            thumbnail_url = f"{settings.PROTOCOL}{settings.PRIMARY_HOST}{thumbnail_url}"

        categories = listing.categories.all().values_list("name", flat=True)

        return {
            "embeds": [
                {
                    "title": f"{version.name} v{version.version_number}",
                    "type": "rich",
                    "description": version.description,
                    "url": f"{listing.get_full_url()}",
                    "timestamp": timezone.now().isoformat(),
                    "color": 4474879,
                    "thumbnail": {
                        "url": thumbnail_url,
                        "width": 256,
                        "height": 256,
                    },
                    "provider": {
                        "name": settings.SITE_NAME,
                        "url": f"{settings.PROTOCOL}{settings.PRIMARY_HOST}/",
                    },
                    "author": {
                        "name": version.package.owner.name,
                    },
                    "fields": [
                        {
                            "name": "Total downloads",
                            "value": f"{version.package.downloads}",
                        },
                        {
                            "name": "Categories",
                            "value": ", ".join(categories),
                        },
                    ],
                }
            ]
        }

    def post_package_version_release(self, version):
        data = self.get_version_release_json(version)
        if data:
            self.call_with_json(data)

    def call_with_json(self, webhook_data):
        if not self.is_active:
            return
        try:
            celery_post.delay(
                self.webhook_url,
                data=json.dumps(webhook_data),
                headers={"Content-Type": "application/json"},
            )
        except Exception as e:
            capture_exception(e)
