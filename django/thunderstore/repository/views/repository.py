from typing import List, Optional, Set, Tuple

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.functional import cached_property
from django.views.generic import TemplateView, View
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView
from django.views.generic.list import ListView

from thunderstore.cache.cache import CacheBustCondition, cache_function_result
from thunderstore.cache.pagination import CachedPaginator
from thunderstore.community.models import (
    Community,
    PackageCategory,
    PackageListing,
    PackageListingReviewStatus,
    PackageListingSection,
)
from thunderstore.repository.mixins import CommunityMixin
from thunderstore.repository.models import PackageVersion, Team, get_package_dependants
from thunderstore.repository.package_upload import PackageUploadForm

# Should be divisible by 4 and 3
MODS_PER_PAGE = 24


class PackageListSearchView(CommunityMixin, ListView):
    model = PackageListing
    paginate_by = MODS_PER_PAGE
    paginator_class = CachedPaginator

    def get_base_queryset(self):
        return self.model.objects.active().exclude(
            ~Q(community__identifier=self.community_identifier)
        )

    def get_page_title(self):
        return ""

    def get_cache_vary(self):
        return ""

    def get_categories(self):
        return PackageCategory.objects.exclude(
            ~Q(community__identifier=self.community_identifier)
        )

    def get_full_cache_vary(self):
        cache_vary = self.get_cache_vary()
        cache_vary += f".{self.community_identifier}"
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

    @cached_property
    def sections(self) -> List[PackageListingSection]:
        return list(
            self.solved_community_from_identifier.package_listing_sections.order_by(
                "-priority",
                "datetime_created",
            ),
        )

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
            )
        if active_ordering == "top-rated":
            return queryset.annotate(
                total_rating=Count("package__package_ratings"),
            ).order_by(
                "-package__is_pinned",
                "package__is_deprecated",
                "-total_rating",
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
            for field in search_fields:
                icontains_query &= ~Q(**{f"{field}__icontains": part})

        return queryset.exclude(icontains_query).distinct()

    def get_queryset(self):
        queryset = (
            self.get_base_queryset()
            .prefetch_related("package__versions", "categories")
            .select_related(
                "package",
                "package__latest",
                "package__owner",
            )
            # .annotate(
            #     _total_downloads=Sum("package__versions__downloads"),
            # )
            # .annotate(
            #     _rating_score=Count("package__package_ratings"),
            # )
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

        if self.solved_community_from_identifier.require_package_listing_approval:
            queryset = queryset.exclude(
                ~Q(review_status=PackageListingReviewStatus.approved),
            )
        else:
            queryset = queryset.exclude(
                review_status=PackageListingReviewStatus.rejected,
            )

        search_query = self.get_search_query()
        if search_query:
            queryset = self.perform_search(queryset, search_query)
        return self.order_queryset(queryset)

    def get_breadcrumbs(self):
        return [
            {
                "url": reverse_lazy("old_urls:packages.list"),
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
        breadcrumbs = self.get_breadcrumbs()
        if len(breadcrumbs) > 1:
            context["breadcrumbs"] = breadcrumbs
        return context


class PackageListView(PackageListSearchView):
    def get_page_title(self):
        return "All mods"

    def get_cache_vary(self):
        return "all"


class PackageListByOwnerView(PackageListSearchView):
    owner: Optional[Team]

    def get_breadcrumbs(self):
        breadcrumbs = super().get_breadcrumbs()
        return breadcrumbs + [
            {
                "url": reverse_lazy(
                    "old_urls:packages.list_by_owner", kwargs=self.kwargs
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
            ~Q(
                Q(package__owner=self.owner)
                & Q(community__identifier=self.community_identifier)
            ),
        )

    def get_page_title(self):
        return f"Mods uploaded by {self.owner.name}"

    def get_cache_vary(self):
        return f"authorer-{self.owner.name}"


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
                community__identifier=self.community_identifier,
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


@cache_function_result(cache_until=CacheBustCondition.any_package_updated)
def get_package_listing_or_404(
    namespace: str,
    name: str,
    community_identifier: str,
) -> PackageListing:
    owner = get_object_or_404(Team, name=namespace)
    package_listing = (
        PackageListing.objects.active()
        .filter(
            package__owner=owner,
            package__name=name,
            community__identifier=community_identifier,
        )
        .select_related(
            "package",
            "package__owner",
            "package__latest",
        )
        .prefetch_related(
            "categories",
        )
        .first()
    )
    if not package_listing:
        raise Http404("No matching package found")
    return package_listing


class PackageDetailView(CommunityMixin, DetailView):
    model = PackageListing

    def get_object(self, *args, **kwargs):
        listing = get_package_listing_or_404(
            namespace=self.kwargs["owner"],
            name=self.kwargs["name"],
            community_identifier=self.community_identifier,
        )
        if not listing.can_be_viewed_by_user(self.request.user):
            raise Http404("Package is waiting for approval or has been rejected")
        return listing

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        package_listing = context["object"]
        dependant_count = len(package_listing.package.dependants_list)

        if dependant_count == 1:
            dependants_string = f"{dependant_count} other mod depends on this mod"
        else:
            dependants_string = f"{dependant_count} other mods depend on this mod"

        context["dependants_string"] = dependants_string
        return context


class PackageVersionDetailView(CommunityMixin, DetailView):
    model = PackageVersion

    def get_object(self, *args, **kwargs):
        owner = self.kwargs["owner"]
        name = self.kwargs["name"]
        version = self.kwargs["version"]
        listing = get_object_or_404(
            PackageListing,
            package__owner__name=owner,
            package__name=name,
            community__identifier=self.community_identifier,
        )
        if not listing.can_be_viewed_by_user(self.request.user):
            raise Http404("Package is waiting for approval or has been rejected")
        if not listing.package.is_active:
            raise Http404("Main package is deactivated")
        return get_object_or_404(
            PackageVersion,
            package=listing.package,
            version_number=version,
        )


class PackageCreateView(CommunityMixin, TemplateView):
    template_name = "repository/package_create.html"

    def dispatch(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return redirect("index")
        return super().dispatch(*args, **kwargs)


class PackageDocsView(CommunityMixin, TemplateView):
    template_name = "repository/package_docs.html"


# TODO: Remove once new UI is stable enough
class PackageCreateOldView(CommunityMixin, CreateView):
    model = PackageVersion
    form_class = PackageUploadForm
    template_name = "repository/package_create_old.html"

    def dispatch(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return redirect("index")
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["selectable_communities"] = Community.objects.filter(
            Q(is_listed=True) | Q(pk=self.solved_community_from_identifier.pk),
        )
        context["current_community"] = self.solved_community_from_identifier
        return context

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super().get_form_kwargs(*args, **kwargs)
        kwargs["user"] = self.request.user
        kwargs["community"] = self.solved_community_from_identifier
        kwargs["initial"] = {
            "team": Team.get_default_for_user(self.request.user),
            "communities": [self.solved_community_from_identifier],
        }
        return kwargs

    @transaction.atomic
    def form_valid(self, form):
        instance = form.save()
        return redirect(instance)


class PackageDownloadView(CommunityMixin, View):
    def get(self, *args, **kwargs):
        owner = kwargs["owner"]
        name = kwargs["name"]
        version = kwargs["version"]

        listing = get_object_or_404(
            PackageListing,
            package__owner__name=owner,
            package__name=name,
            community__identifier=self.community_identifier,
        )
        version = get_object_or_404(
            PackageVersion,
            package=listing.package,
            version_number=version,
        )
        version.maybe_increase_download_counter(self.request)
        return redirect(self.request.build_absolute_uri(version.file.url))
