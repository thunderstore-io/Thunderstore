from django.db import models
from django.db.models import Manager
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


class Wiki(TimestampMixin, TitleMixin):
    objects: Manager["Wiki"]


class WikiPage(TimestampMixin, TitleMixin):
    objects: Manager["WikiPage"]

    wiki = models.ForeignKey(
        "thunderstore_wiki.Wiki",
        related_name="pages",
        on_delete=models.CASCADE,
    )
    markdown_content = models.TextField(blank=True, null=True)
