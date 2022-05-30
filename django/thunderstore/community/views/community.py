from django.conf import settings
from django.db.models import BigIntegerField, Count, Sum
from django.shortcuts import redirect
from django.views import View
from django.views.generic.list import ListView

from thunderstore.cache.cache import CacheBustCondition
from thunderstore.cache.pagination import CachedPaginator
from thunderstore.community.models.community_site import CommunitySite

# Should be divisible by 4 and 3
MODS_PER_PAGE = 24


class CommunitiesView(ListView):
    model = CommunitySite
    paginate_by = MODS_PER_PAGE
    paginator_class = CachedPaginator
    template_name = "community/communities_list.html"

    def get_base_queryset(self):
        return self.model.objects.exclude(is_listed=False)

    def get_page_title(self):
        return "Communities"

    def get_cache_vary(self):
        return "communities"

    def get_full_cache_vary(self):
        cache_vary = self.get_cache_vary()
        return cache_vary

    def order_queryset(self, queryset):
        return (
            queryset.prefetch_related()
            .annotate(
                total_downloads=Sum(
                    "community__package_listings__package__versions__downloads",
                    output_field=BigIntegerField(),
                ),
                package_count=Count("community__package_listings"),
            )
            .order_by(
                "-total_downloads",
                "community__name",
            )
        )

    def get_queryset(self):
        return self.order_queryset(self.get_base_queryset())

    def get_paginator(
        self,
        queryset,
        per_page,
        orphans=0,
        allow_empty_first_page=True,
        **kwargs,
    ):
        return self.paginator_class(
            queryset,
            per_page,
            cache_key="community.communities.paginator",
            cache_vary=self.get_full_cache_vary(),
            cache_bust_condition=CacheBustCondition.dynamic_html_updated,
            orphans=orphans,
            allow_empty_first_page=allow_empty_first_page,
        )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["cache_vary"] = self.get_full_cache_vary()
        context["page_title"] = self.get_page_title()
        context["game_count"] = len(self.object_list)
        return context


class FaviconView(View):
    def get(self, *args, **kwargs):
        if self.request.community_site.favicon:
            return redirect(self.request.community_site.favicon.url)
        return redirect(f"{settings.STATIC_URL}favicon.ico")
