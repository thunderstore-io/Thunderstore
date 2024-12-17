from typing import TYPE_CHECKING, Literal, Optional, Union

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from thunderstore.core.types import UserType
from thunderstore.repository.permissions import ensure_can_rate_package

if TYPE_CHECKING:
    from thunderstore.repository.models import Package


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
            PackageRating.objects.get_or_create(rater=agent, package=package)
            return "rated"
        else:
            PackageRating.objects.filter(rater=agent, package=package).delete()
            return "unrated"
