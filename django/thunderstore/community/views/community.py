from typing import List, Optional, Set, Tuple

from django.db.models import Q
from django.utils.functional import cached_property
from django.views.generic.list import ListView

from thunderstore.cache.cache import CacheBustCondition
from thunderstore.cache.pagination import CachedPaginator
from thunderstore.community.models import Community
from thunderstore.community.models.community_site import CommunitySite
from thunderstore.repository.mixins import CommunityMixin

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
        cache_vary += f".{self.get_search_query()}"
        return cache_vary

    def get_search_query(self):
        return self.request.GET.get("q", "")

    def order_queryset(self, queryset):
        return queryset.order_by(
            "community__name",
        )

    def perform_search(self, queryset, search_query):
        search_fields = (
            "community__name",
            "community__identifier",
        )

        icontains_query = Q()
        parts = [x for x in search_query.split(" ") if x]
        for part in parts:
            for field in search_fields:
                icontains_query &= ~Q(**{f"{field}__icontains": part})

        return queryset.exclude(icontains_query).distinct()

    def get_queryset(self):
        queryset = self.get_base_queryset()

        search_query = self.get_search_query()
        if search_query:
            queryset = self.perform_search(queryset, search_query)
        return self.order_queryset(queryset)

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
        context["current_search"] = self.get_search_query()
        return context
