from datetime import datetime

from django.db import models, transaction
from django.db.models import Manager
from django.urls import reverse

from django_contracts.compat import TimestampMixin
from django_contracts.models.publishable import PublishableMixin, PublishStatus


class LegalContract(TimestampMixin, PublishableMixin):
    objects: Manager["LegalContract"]
    versions: Manager["LegalContractVersion"]

    title = models.CharField(max_length=128)
    slug = models.SlugField(max_length=128, unique=True)
    latest = models.ForeignKey(
        "contracts.LegalContractVersion",
        related_name="+",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    def recache_latest(self):
        self.latest = (
            self.versions.filter(
                publish_status=PublishStatus.PUBLISHED,
            )
            .exclude(datetime_published=None)
            .order_by("-datetime_published")
            .first()
        )
        self.save()

    def get_absolute_url(self):
        return reverse(
            "contracts:contract",
            kwargs={
                "contract": self.slug,
            },
        )

    def __str__(self):
        return self.title


class LegalContractVersion(TimestampMixin, PublishableMixin):
    contract = models.ForeignKey(
        to="contracts.LegalContract",
        related_name="versions",
        on_delete=models.PROTECT,
    )
    html_content = models.TextField(blank=True, null=True)
    markdown_content = models.TextField(blank=True, null=True)

    @property
    def effective_date(self) -> datetime:
        return self.datetime_published or self.datetime_updated

    @property
    def is_latest(self) -> bool:
        return self.contract.latest == self

    @transaction.atomic
    def publish(self):
        super().publish()
        self.contract.recache_latest()

    def get_absolute_url(self):
        return reverse(
            "contracts:contract.version",
            kwargs={
                "contract": self.contract.slug,
                "version": self.pk,
            },
        )

    def __str__(self):
        return f"{self.contract} - {self.datetime_created.isoformat()} - {self.publish_status}"
