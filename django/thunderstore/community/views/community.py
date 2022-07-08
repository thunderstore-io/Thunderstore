from django.conf import settings
from django.db.models import BigIntegerField, Count, Sum
from django.shortcuts import redirect
from django.views import View
from django.views.generic.list import ListView

from thunderstore.cache.cache import CacheBustCondition
from thunderstore.cache.pagination import CachedPaginator
from thunderstore.community.models.community_site import CommunitySite
from thunderstore.repository.models.package import Package

# Should be divisible by 5, 3 and 2
GAMES_PER_PAGE = 30


class CommunitiesView(ListView):
    model = CommunitySite
    paginate_by = GAMES_PER_PAGE
    paginator_class = CachedPaginator
    template_name = "community/communities_list.html"

    def get_base_queryset(self):
        return self.model.objects.exclude(is_listed=False).prefetch_related()

    def get_page_title(self):
        return "Communities"

    def get_cache_vary(self):
        return "communities"

    def order_queryset(self, queryset):
        return queryset.annotate(
            total_downloads=Sum(
                "community__package_listings__package__versions__downloads",
                output_field=BigIntegerField(),
            ),
        ).order_by(
            "-total_downloads",
            "community__name",
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
            cache_vary=self.get_cache_vary(),
            cache_bust_condition=CacheBustCondition.dynamic_html_updated,
            orphans=orphans,
            allow_empty_first_page=allow_empty_first_page,
        )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["cache_vary"] = self.get_cache_vary()
        context["page_title"] = self.get_page_title()
        context["game_count"] = len(self.object_list)
        context["mod_count"] = Package.objects.filter(is_active=True).count()
        return context


class FaviconView(View):
    def get(self, *args, **kwargs):
        if self.request.community_site.favicon:
            return redirect(self.request.community_site.favicon.url)
        return redirect(f"{settings.STATIC_URL}favicon.ico")
