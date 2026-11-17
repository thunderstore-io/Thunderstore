from django.contrib import admin
from django.http import HttpRequest

from thunderstore.ts_trending.models import (
    ListingScore,
    NewAndTrendingScore,
    TrendingScore,
)


class ListingScoreAdmin(admin.ModelAdmin):
    list_display = (
        "listing",
        "community",
        "score",
        "datetime_computed",
    )
    list_select_related = (
        "listing__package",
        "listing__community",
    )
    ordering = ("-score",)
    search_fields = (
        "listing__package__name",
        "listing__package__owner__name",
        "listing__community__identifier",
    )

    def community(self, obj: ListingScore) -> str:
        return obj.listing.community.identifier

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False


@admin.register(TrendingScore)
class TrendingScoreAdmin(ListingScoreAdmin):
    pass


@admin.register(NewAndTrendingScore)
class NewAndTrendingScoreAdmin(ListingScoreAdmin):
    pass
