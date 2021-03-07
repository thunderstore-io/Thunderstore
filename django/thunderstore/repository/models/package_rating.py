from django.conf import settings
from django.db import models


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
