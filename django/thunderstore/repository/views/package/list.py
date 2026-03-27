from typing import List, Optional, Set, Tuple

from django.core.exceptions import PermissionDenied
from django.db.models import Count, OuterRef, Q, QuerySet, Subquery, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import ListView

from thunderstore.cache.enums import CacheBustCondition
from thunderstore.cache.pagination import CachedPaginator
from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.models import (
    PackageCategory,
    PackageListing,
    PackageListingSection,
)
from thunderstore.frontend.url_reverse import get_community_url_reverse_args
from thunderstore.repository.mixins import CommunityMixin
from thunderstore.repository.models import Team, get_package_dependants
from thunderstore.repository.views.package._utils import get_moderatable_communities

# Should be divisible by 4 and 3
MODS_PER_PAGE = 24


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PackageListSearchView(CommunityMixin, ListView):
    model = PackageListing
    paginate_by = MODS_PER_PAGE
    paginator_class = CachedPaginator

    def filter_community(
        self, queryset: QuerySet[PackageListing]
    ) -> QuerySet[PackageListing]:
        return queryset.exclude(~Q(community=self.community))

    def get_community_cache_vary(self) -> str:
        return self.community_identifier

    def get_base_queryset(self) -> QuerySet[PackageListing]:
        return self.filter_community(self.model.objects.active())

    def get_page_title(self):
        return ""

    def get_cache_vary(self):
        return ""

    def get_categories(self):
        return PackageCategory.objects.exclude(~Q(community=self.community))

    def get_full_cache_vary(self):
        cache_vary = self.get_cache_vary()
        cache_vary += f".{self.get_community_cache_vary()}"
        cache_vary += f".{self.get_search_query()}"
        cache_vary += f".{self.get_active_ordering()}"
        cache_vary += f".{self.get_included_categories()}"
        cache_vary += f".{self.get_excluded_categories()}"
        cache_vary += f".{self.get_is_deprecated_included()}"
        cache_vary += f".{self.get_is_nsfw_included()}"
        cache_vary += f".{self.active_section_slug}"
        return cache_vary

    def get_ordering_choices(self):
        return (
            ("last-updated", "Last updated"),
            ("newest", "Newest"),
            ("most-downloaded", "Most downloaded"),
            ("top-rated", "Top rated"),
        )

    def get_sections(self) -> QuerySet[PackageListingSection]:
        return self.community.package_listing_sections.order_by(
            "-priority",
            "datetime_created",
        )

    @cached_property
    def sections(self) -> List[PackageListingSection]:
        return list(self.get_sections())

    @cached_property
    def section_choices(self) -> List[Tuple[str, str]]:
        return [(x.slug, x.name) for x in self.sections if x.is_listed]

    @cached_property
    def active_section(self) -> Optional[PackageListingSection]:
        section_param = self.request.GET.get("section", None)
        if section_param is not None:
            # Avoiding querying the database, should be faster as long as there
            # aren't massive amounts of sections
            for entry in self.sections:
                if entry.slug == section_param:
                    return entry
            raise Http404()
        elif self.sections:
            return self.sections[0]
        return None

    @cached_property
    def active_section_slug(self) -> str:
        return self.active_section.slug if self.active_section else ""

    def _get_int_list(self, name: str) -> List[int]:
        selections = self.request.GET.getlist(name, [])
        result = []
        for selection in selections:
            try:
                result.append(int(selection))
            except ValueError:
                pass
        return result

    def get_included_categories(self):
        return self._get_int_list("included_categories")

    @property
    def filter_require_categories(self) -> Set[int]:
        categories = set(self.get_included_categories())
        if self.active_section:
            categories.update(
                self.active_section.require_categories.values_list("pk", flat=True),
            )
        return categories

    def get_excluded_categories(self):
        return self._get_int_list("excluded_categories")

    @property
    def filter_exclude_categories(self) -> Set[int]:
        categories = set(self.get_excluded_categories())
        if self.active_section:
            categories.update(
                self.active_section.exclude_categories.values_list("pk", flat=True),
            )
        return categories

    def get_is_nsfw_included(self):
        try:
            return bool(self.request.GET.get("nsfw", False))
        except ValueError:
            return False

    def get_is_deprecated_included(self):
        try:
            return bool(self.request.GET.get("deprecated", False))
        except ValueError:
            return False

    def get_active_ordering(self):
        ordering = self.request.GET.get("ordering", "last-updated")
        possibilities = [x[0] for x in self.get_ordering_choices()]
        if ordering not in possibilities:
            return possibilities[0]
        return ordering

    def get_search_query(self):
        return self.request.GET.get("q", "")

    def order_queryset(self, queryset):
        active_ordering = self.get_active_ordering()
        if active_ordering == "newest":
            return queryset.order_by(
                "-package__is_pinned",
                "package__is_deprecated",
                "-package__date_created",
            )
        if active_ordering == "most-downloaded":
            return queryset.annotate(
                total_downloads=Sum("package__versions__downloads"),
            ).order_by(
                "-package__is_pinned",
                "package__is_deprecated",
                "-total_downloads",
                "-package__date_updated",
            )
        if active_ordering == "top-rated":
            return queryset.annotate(
                total_rating=Count("package__package_ratings"),
            ).order_by(
                "-package__is_pinned",
                "package__is_deprecated",
                "-total_rating",
                "-package__date_updated",
            )
        return queryset.order_by(
            "-package__is_pinned",
            "package__is_deprecated",
            "-package__date_updated",
        )

    def perform_search(self, queryset, search_query):
        search_fields = (
            "package__name",
            "package__owner__name",
            "package__latest__description",
        )

        icontains_query = Q()
        parts = [x for x in search_query.split(" ") if x]

        for part in parts:
            part_query = Q()
            for field in search_fields:
                part_query |= Q(**{f"{field}__icontains": part})
            icontains_query &= part_query

        return queryset.filter(icontains_query).distinct()

    def filter_approval_status(
        self, queryset: QuerySet[PackageListing]
    ) -> QuerySet[PackageListing]:
        if self.community.require_package_listing_approval:
            return queryset.exclude(
                ~Q(review_status=PackageListingReviewStatus.approved),
            )
        else:
            return queryset.exclude(
                review_status=PackageListingReviewStatus.rejected,
            )

    def get_queryset(self):
        listing_ref = PackageListing.objects.filter(pk=OuterRef("pk"))

        queryset = (
            self.get_base_queryset()
            .prefetch_related(
                "package__versions",
                "community__sites",
                "categories",
            )
            .select_related(
                "package",
                "package__latest",
                "package__owner",
                "community",
            )
            .annotate(
                _total_downloads=Subquery(
                    listing_ref.annotate(
                        downloads=Sum("package__versions__downloads"),
                    ).values("downloads"),
                ),
                _rating_score=Subquery(
                    listing_ref.annotate(
                        ratings=Count("package__package_ratings"),
                    ).values("ratings"),
                ),
            )
        )

        included_categories = self.filter_require_categories
        if included_categories:
            include_categories_qs = Q()
            for category in included_categories:
                include_categories_qs |= Q(categories=category)
            queryset = queryset.exclude(~include_categories_qs)

        excluded_categories = self.filter_exclude_categories
        if excluded_categories:
            exclude_categories_qs = Q()
            for category in excluded_categories:
                exclude_categories_qs |= Q(categories=category)
            queryset = queryset.exclude(exclude_categories_qs)

        if not self.get_is_nsfw_included():
            queryset = queryset.exclude(has_nsfw_content=True)

        if not self.get_is_deprecated_included():
            queryset = queryset.exclude(package__is_deprecated=True)

        queryset = self.filter_approval_status(queryset)

        search_query = self.get_search_query()
        if search_query:
            queryset = self.perform_search(queryset, search_query)
        return self.order_queryset(queryset)

    def get_breadcrumbs(self):
        return [
            {
                "url": reverse_lazy(
                    **get_community_url_reverse_args(
                        community=self.community,
                        viewname="packages.list",
                    )
                ),
                "name": "Packages",
            },
        ]

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
            cache_key="repository.package_list.paginator",
            cache_vary=self.get_full_cache_vary(),
            cache_bust_condition=CacheBustCondition.any_package_updated,
            orphans=orphans,
            allow_empty_first_page=allow_empty_first_page,
        )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["categories"] = self.get_categories()
        context["included_categories"] = self.get_included_categories()
        context["excluded_categories"] = self.get_excluded_categories()
        context["nsfw_included"] = self.get_is_nsfw_included()
        context["deprecated_included"] = self.get_is_deprecated_included()
        context["cache_vary"] = self.get_full_cache_vary()
        context["page_title"] = self.get_page_title()
        context["ordering_modes"] = self.get_ordering_choices()
        context["sections"] = self.section_choices
        context["active_section"] = self.active_section_slug
        context["active_ordering"] = self.get_active_ordering()
        context["current_search"] = self.get_search_query()
        context["allowed_params"] = {
            "q",
            "ordering",
            "deprecated",
            "nsfw",
            "excluded_categories",
            "included_categories",
            "section",
            "page",
        }
        breadcrumbs = self.get_breadcrumbs()
        if len(breadcrumbs) > 1:
            context["breadcrumbs"] = breadcrumbs
        return context


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PackageListView(PackageListSearchView):
    def get_page_title(self):
        return "All mods"

    def get_cache_vary(self):
        return "all"


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PackageListByOwnerView(PackageListSearchView):
    owner: Optional[Team]

    def get_breadcrumbs(self):
        breadcrumbs = super().get_breadcrumbs()
        return breadcrumbs + [
            {
                "url": reverse_lazy(
                    **get_community_url_reverse_args(
                        community=self.community,
                        viewname="packages.list_by_owner",
                        kwargs=self.kwargs,
                    )
                ),
                "name": self.owner.name,
            },
        ]

    def cache_owner(self):
        self.owner = get_object_or_404(Team, name=self.kwargs["owner"])

    def dispatch(self, *args, **kwargs):
        self.cache_owner()
        return super().dispatch(*args, **kwargs)

    def get_base_queryset(self):
        return self.model.objects.active().exclude(
            ~Q(Q(package__owner=self.owner) & Q(community=self.community)),
        )

    def get_page_title(self):
        return f"Mods uploaded by {self.owner.name}"

    def get_cache_vary(self):
        return f"authorer-{self.owner.name}"


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PackageListByDependencyView(PackageListSearchView):
    package_listing: PackageListing

    def cache_package_listing(self):
        owner = self.kwargs["owner"]
        owner = get_object_or_404(Team, name=owner)
        name = self.kwargs["name"]
        package_listing = (
            self.model.objects.active()
            .filter(
                package__owner=owner,
                package__name=name,
                community=self.community,
            )
            .first()
        )
        if not package_listing:
            raise Http404("No matching package found")
        self.package_listing = package_listing

    def dispatch(self, *args, **kwargs):
        self.cache_package_listing()
        return super().dispatch(*args, **kwargs)

    def get_base_queryset(self):
        return PackageListing.objects.exclude(
            ~Q(package__in=get_package_dependants(self.package_listing.package.pk)),
        )

    def get_page_title(self):
        return f"Mods that depend on {self.package_listing.package.display_name}"

    def get_cache_vary(self):
        return f"dependencies-{self.package_listing.package.id}"


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PackageReviewListView(PackageListSearchView):
    community_ids: List[str] = []

    def filter_community(
        self, queryset: QuerySet[PackageListing]
    ) -> QuerySet[PackageListing]:
        return queryset.exclude(~Q(community_id__in=self.community_ids))

    def filter_approval_status(
        self, queryset: QuerySet[PackageListing]
    ) -> QuerySet[PackageListing]:
        return queryset

    def get_community_cache_vary(self) -> str:
        return ".".join(self.community_ids)

    def get_base_queryset(self) -> QuerySet[PackageListing]:
        queryset = super().get_base_queryset()
        return queryset.exclude(is_review_requested=False)

    def get_sections(self) -> QuerySet[PackageListingSection]:
        return PackageListingSection.objects.none()

    def get_page_title(self):
        return "Review queue"

    def get_cache_vary(self):
        return f"review-queue"

    def dispatch(self, *args, **kwargs):
        self.community_ids = get_moderatable_communities(self.request.user)
        if not self.community_ids:
            raise PermissionDenied()
        return super().dispatch(*args, **kwargs)
