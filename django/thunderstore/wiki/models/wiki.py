from django.db import models, transaction
from django.db.models import Manager
from django.utils import timezone
from django.utils.text import slugify

from django_contracts.compat import TimestampMixin


class TitleMixin(models.Model):
    title = models.CharField(max_length=512)
    slug = models.CharField(max_length=512)

    class Meta:
        abstract = True

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    @property
    def full_slug(self) -> str:
        return f"{self.pk}-{self.slug}"


class Wiki(TimestampMixin, TitleMixin):
    objects: Manager["Wiki"]

    def on_page_updated(self):
        self.datetime_updated = timezone.now()
        self.save()


class WikiPage(TimestampMixin, TitleMixin):
    objects: Manager["WikiPage"]

    wiki = models.ForeignKey(
        "thunderstore_wiki.Wiki",
        related_name="pages",
        on_delete=models.CASCADE,
    )
    markdown_content = models.TextField(blank=True, null=True)

    @transaction.atomic
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.wiki.on_page_updated()

    @transaction.atomic
    def delete(self, *args, **kwargs):
        res = super().delete(*args, **kwargs)
        self.wiki.on_page_updated()
        return res
