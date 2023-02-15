from django.db import models
from django.utils import timezone


class PublishStatus(models.TextChoices):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"


class PublishableMixin(models.Model):
    publish_status = models.TextField(
        choices=PublishStatus.choices,
        blank=False,
        null=False,
        default=PublishStatus.DRAFT,
    )
    datetime_published = models.DateTimeField(blank=True, null=True)

    def publish(self):
        if self.datetime_published is None:
            self.datetime_published = timezone.now()
        self.publish_status = PublishStatus.PUBLISHED
        self.save()

    class Meta:
        abstract = True
