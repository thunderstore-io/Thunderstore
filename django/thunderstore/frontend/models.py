from typing import List, Optional

from django.db import models
from django.db.models import Manager, Q, TextChoices, signals

from thunderstore.cache.enums import CacheBustCondition
from thunderstore.cache.tasks import invalidate_cache_on_commit_async
from thunderstore.community.models import Community
from thunderstore.core.mixins import TimestampMixin
from thunderstore.core.utils import ChoiceEnum


class DynamicPlacement(ChoiceEnum):
    ads_txt = "ads_txt"
    robots_txt = "robots_txt"
    html_head = "html_head"
    html_body_beginning = "html_body_beginning"
    nav_bar_right_nav = "nav_bar_right_nav"
    content_beginning = "content_beginning"
    footer_top = "footer_top"
    footer_bottom = "footer_bottom"
    content_end = "content_end"
    package_page_actions = "package_page_actions"
    main_content_left = "main_content_left"
    main_content_right = "main_content_right"


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

    exclude_user_flags = models.ManyToManyField(
        "account.UserFlag",
        related_name="dynamic_html_exclusions",
        help_text="Hidden from user with at least one of these flags",
        blank=True,
    )
    require_user_flags = models.ManyToManyField(
        "account.UserFlag",
        help_text="Shown to users with at least one of these flags",
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
    def get_for_community(
        cls,
        community: Optional[Community],
        placement: Optional[str],
        user_flags: List[str],
    ):
        if community:
            community_filter = Q(
                ~Q(exclude_communities=community)
                & Q(Q(require_communities=None) | Q(require_communities=community))
            )
        else:
            community_filter = Q(require_communities=None)

        user_filter = Q(
            ~Q(exclude_user_flags__identifier__in=user_flags)
            & Q(
                Q(require_user_flags__identifier__in=user_flags)
                | Q(require_user_flags=None)
            )
        )
        query = Q(is_active=True) & community_filter & user_filter
        if placement:
            query = query & Q(placement=placement)

        return cls.objects.filter(query).order_by("-ordering", "-pk")


class LinkTargetChoices(TextChoices):
    Blank = "_blank"
    Parent = "_parent"
    Self = "_self"
    Top = "_top"


class LinkMixin(TimestampMixin):
    title = models.TextField()
    href = models.TextField()
    css_class = models.TextField(blank=True, null=True)
    target = models.TextField(
        choices=LinkTargetChoices.choices,
        default=LinkTargetChoices.Self,
    )
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title

    class Meta:
        abstract = True


class NavLink(LinkMixin):
    objects: Manager["NavLink"]

    class Meta:
        ordering = ("order", "title")
        indexes = [models.Index(fields=["is_active", "order", "title"])]


class CommunityNavLink(LinkMixin):
    objects: Manager["CommunityNavLink"]

    community = models.ForeignKey(
        "community.Community",
        related_name="nav_links",
        on_delete=models.CASCADE,
    )

    class Meta:
        ordering = ("order", "title")
        indexes = [models.Index(fields=["community", "is_active", "order", "title"])]


class FooterLink(LinkMixin):
    objects: Manager["FooterLink"]
    group_title = models.TextField()

    class Meta:
        ordering = ("order", "title")
        indexes = [models.Index(fields=["is_active", "group_title", "order", "title"])]


signals.post_save.connect(DynamicHTML.post_save, sender=DynamicHTML)
