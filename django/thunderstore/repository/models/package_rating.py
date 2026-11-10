from datetime import datetime
from typing import TYPE_CHECKING, Literal, Optional, Union

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from pydantic import BaseModel

from thunderstore.core.types import UserType
from thunderstore.repository.permissions import ensure_can_rate_package
from thunderstore.ts_analytics.kafka import KafkaTopic, generate_event_id
from thunderstore.ts_analytics.tasks import send_kafka_message

if TYPE_CHECKING:
    from thunderstore.repository.models import Package


class AnalyticsEventPackageLike(BaseModel):
    id: int
    package_id: int
    action: Literal["like", "unlike"]
    timestamp: datetime


def _send_package_like_event(
    package_id: int, action: Literal["like", "unlike"]
) -> None:
    payload = AnalyticsEventPackageLike(
        id=generate_event_id(),
        package_id=package_id,
        action=action,
        timestamp=timezone.now(),
    )
    transaction.on_commit(
        lambda: send_kafka_message.delay(
            topic=KafkaTopic.A_PACKAGE_LIKE_V1,
            payload_string=payload.json(),
        )
    )


class PackageRating(models.Model):
    rater = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="package_ratings",
        on_delete=models.CASCADE,
    )
    package = models.ForeignKey(
        "repository.Package",
        on_delete=models.CASCADE,
        related_name="package_ratings",
    )
    date_created = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("rater", "package"), name="one_rating_per_rater"
            ),
        ]

    def __str__(self):
        return f"{self.rater.username} rating on {self.package.full_package_name}"

    @classmethod
    def rate_package(
        cls,
        agent: Optional[UserType],
        package: "Package",
        target_state: Union[Literal["rated"], Literal["unrated"]],
    ) -> Union[Literal["rated"], Literal["unrated"]]:
        if target_state not in ("rated", "unrated"):
            raise ValidationError("Invalid target_state")

        ensure_can_rate_package(agent, package)

        if target_state == "rated":
            _, created = PackageRating.objects.get_or_create(
                rater=agent, package=package
            )
            if created:
                _send_package_like_event(package.pk, "like")
            return "rated"
        else:
            deleted, _ = PackageRating.objects.filter(
                rater=agent, package=package
            ).delete()
            if deleted:
                _send_package_like_event(package.pk, "unlike")
            return "unrated"
