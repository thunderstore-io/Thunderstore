from django.db import models
from django.db.models import Q, signals

from thunderstore.cache.enums import CacheBustCondition
from thunderstore.cache.tasks import invalidate_cache_on_commit_async
from thunderstore.core.utils import ChoiceEnum


class DynamicPlacement(ChoiceEnum):
    ads_txt = "ads_txt"
    robots_txt = "robots_txt"
    html_head = "html_head"
    html_body_beginning = "html_body_beginning"
    content_beginning = "content_beginning"
    content_end = "content_end"
    frontpage_beginning = "frontpage_beginning"
    frontpage_end = "frontpage_end"


class DynamicHTML(models.Model):
    name = models.CharField(
        max_length=256,
    )
    content = models.TextField(
        null=True,
        blank=True,
    )
    placement = models.CharField(
        max_length=256,
        db_index=True,
        choices=DynamicPlacement.as_choices(),
    )
    ordering = models.IntegerField(
        default=0,
    )

    is_active = models.BooleanField(
        default=True,
    )
    date_created = models.DateTimeField(
        auto_now_add=True,
    )
    date_modified = models.DateTimeField(
        auto_now=True,
    )

    exclude_communities = models.ManyToManyField(
        "community.Community",
        related_name="dynamic_html_exclusions",
        blank=True,
    )
    require_communities = models.ManyToManyField(
        "community.Community",
        related_name="dynamic_html_inclusions",
        blank=True,
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Dynamic HTML"
        verbose_name_plural = "Dynamic HTML"

    @staticmethod
    def post_save(sender, instance, created, **kwargs):
        invalidate_cache_on_commit_async(CacheBustCondition.dynamic_html_updated)

    @classmethod
    def get_for_community(cls, community, placement):
        community_filter = Q(
            ~Q(exclude_communities=community)
            & Q(Q(require_communities=None) | Q(require_communities=community))
        )
        full_query = Q(Q(is_active=True) & Q(placement=placement) & community_filter)
        return cls.objects.filter(full_query).order_by("-ordering", "-pk")


signals.post_save.connect(DynamicHTML.post_save, sender=DynamicHTML)
