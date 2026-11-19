from django.db import models


class ListingScore(models.Model):
    listing = models.OneToOneField(
        "community.PackageListing",
        on_delete=models.CASCADE,
        primary_key=True,
    )
    score = models.FloatField()
    datetime_computed = models.DateTimeField()

    class Meta:
        abstract = True

    def __str__(self) -> str:
        return f"{self.listing}: {self.score}"


class TrendingScore(ListingScore):
    pass


class NewAndTrendingScore(ListingScore):
    pass
