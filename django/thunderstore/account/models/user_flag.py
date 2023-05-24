import datetime
from typing import List, Optional, Union

from cachalot.api import cachalot_disabled
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Manager, Q

from thunderstore.core.mixins import TimestampMixin
from thunderstore.core.types import UserType


class UserFlag(TimestampMixin):
    objects: Manager["UserFlag"]

    name = models.TextField()
    description = models.TextField(blank=True)
    app_label = models.CharField(
        max_length=100,  # Copied from Django's ContentType model
        help_text="The Django app label of the app that provided this flag type",
    )
    identifier = models.SlugField(
        unique=True,
        help_text="The globally unique identifier for this flag type",
    )

    def __str__(self):
        return f"{self.app_label}: {self.name}"

    @classmethod
    def get_active_flags_on_user(
        cls,
        user: Optional[Union[UserType, AnonymousUser]],
        timestamp: datetime.datetime,
    ) -> List[str]:
        if not user or not user.pk:
            return []

        query = Q(user=user, datetime_valid_from__lte=timestamp) & Q(
            Q(datetime_valid_until__gt=timestamp) | Q(datetime_valid_until=None)
        )

        # The query parameters are almost always unique due to the timestamp, so
        # it makes no sense to cache the query.
        with cachalot_disabled():
            return list(
                UserFlagMembership.objects.filter(query)
                .order_by("flag__identifier")
                .distinct("flag__identifier")
                .values_list("flag__identifier", flat=True)
            )


class UserFlagMembership(TimestampMixin):
    """
    The UserFlagMembership model is intended as a generic system for attaching
    UserFlags to specific users. The goal of the flags is to allow querying for
    users with specific flags enabled in an efficient manner.
    """

    objects: Manager["UserFlagMembership"]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="flags",
        on_delete=models.CASCADE,
    )
    flag = models.ForeignKey(
        "account.UserFlag",
        related_name="users",
        on_delete=models.CASCADE,
    )
    datetime_valid_from = models.DateTimeField()
    datetime_valid_until = models.DateTimeField(blank=True, null=True)

    related_object_type = models.ForeignKey(
        ContentType,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    related_object_id = models.PositiveIntegerField(blank=True, null=True)
    related_object = GenericForeignKey(
        ct_field="related_object_type",
        fk_field="related_object_id",
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["user", "datetime_valid_from", "-datetime_valid_until"],
            ),
            models.Index(
                fields=["related_object_type", "related_object_id"],
            ),
        ]
