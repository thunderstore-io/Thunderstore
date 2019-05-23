from django.contrib.postgres.search import TrigramSimilarity, SearchVector, SearchQuery
from django.db import transaction
from django.db.models import Q, Sum
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView
from django.views.generic import View

from repository.models import Package
from repository.models import PackageVersion
from repository.models import UploaderIdentity
from repository.models import UploaderIdentityMember
from repository.models import UploaderIdentityMemberRole
from repository.ziptools import PackageVersionForm

from django.shortcuts import redirect, get_object_or_404

MODS_PER_PAGE = 20


class PackageListSearchView(ListView):
    model = Package
    paginate_by = MODS_PER_PAGE

    def get_base_queryset(self):
        return Package.objects

    def get_page_title(self):
        return ""

    def get_cache_vary(self):
        return ""

    def get_full_cache_vary(self):
        cache_vary = self.get_cache_vary()
        cache_vary += f".{self.get_search_query()}"
        cache_vary += f".{self.get_active_ordering()}"
        return cache_vary

    def get_ordering_choices(self):
        return (
            ("last-updated", "Last updated"),
            ("newest", "Newest"),
            ("most-downloaded", "Most downloaded"),
        )

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
            return queryset.order_by("-is_pinned", "-date_created")
        if active_ordering == "most-downloaded":
            return queryset.annotate(
                total_downloads=Sum("versions__downloads")
            ).order_by("-is_pinned", "-total_downloads")
        return queryset.order_by("-is_pinned", "-date_updated")

    def perform_search(self, queryset, search_query):
        search_fields = ("name", "owner__name")
        # TODO: Add description once we can get the latest one from the db
        return (
            queryset.annotate(name_search_score=TrigramSimilarity("name", search_query))
            .annotate(search=SearchVector(*search_fields))
            .exclude(
                Q(name_search_score__lte=0.1) & ~Q(search=SearchQuery(search_query))
            )
            .distinct()
        )

    def get_queryset(self):
        queryset = (
            self.get_base_queryset()
            .exclude(is_active=False)
            .prefetch_related("versions")
        )
        search_query = self.get_search_query()
        if search_query:
            queryset = self.perform_search(queryset, search_query)
        return self.order_queryset(queryset)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["cache_vary"] = self.get_full_cache_vary()
        context["page_title"] = self.get_page_title()
        context["ordering_modes"] = self.get_ordering_choices()
        context["active_ordering"] = self.get_active_ordering()
        context["current_search"] = self.get_search_query()
        return context


class PackageListView(PackageListSearchView):
    def get_page_title(self):
        return f"All mods"

    def get_cache_vary(self):
        return "all"


class PackageListByOwnerView(PackageListSearchView):
    def cache_owner(self):
        self.owner = get_object_or_404(UploaderIdentity, name=self.kwargs["owner"])

    def dispatch(self, *args, **kwargs):
        self.cache_owner()
        return super().dispatch(*args, **kwargs)

    def get_base_queryset(self):
        return self.model.objects.exclude(~Q(owner=self.owner))

    def get_page_title(self):
        return f"Mods uploaded by {self.owner.name}"

    def get_cache_vary(self):
        return f"authorer-{self.owner.name}"


class PackageListByDependencyView(PackageListSearchView):
    model = Package
    paginate_by = MODS_PER_PAGE

    def cache_package(self):
        owner = self.kwargs["owner"]
        owner = get_object_or_404(UploaderIdentity, name=owner)
        name = self.kwargs["name"]
        package = get_object_or_404(self.model, is_active=True, owner=owner, name=name)
        self.package = package

    def dispatch(self, *args, **kwargs):
        self.cache_package()
        return super().dispatch(*args, **kwargs)

    def get_base_queryset(self):
        return self.package.dependants

    def get_page_title(self):
        return f"Mods that depend on {self.package.display_name}"

    def get_cache_vary(self):
        return f"dependencies-{self.package.id}"


class PackageDetailView(DetailView):
    model = Package

    def get_object(self, *args, **kwargs):
        owner = self.kwargs["owner"]
        owner = get_object_or_404(UploaderIdentity, name=owner)
        name = self.kwargs["name"]
        return get_object_or_404(self.model, is_active=True, owner=owner, name=name)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        dependants_string = ""
        package = context["object"]
        dependant_count = package.dependants.filter(is_active=True).count()

        if dependant_count == 1:
            dependants_string = f"{dependant_count} other mod depends on this mod"
        else:
            dependants_string = f"{dependant_count} other mods depend on this mod"

        context["dependants_string"] = dependants_string
        return context


class PackageCreateView(CreateView):
    model = PackageVersion
    form_class = PackageVersionForm
    template_name = "repository/package_create.html"

    def dispatch(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return redirect("index")
        return super(PackageCreateView, self).dispatch(*args, **kwargs)

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super(PackageCreateView, self).get_form_kwargs(*args, **kwargs)
        kwargs["owner"] = UploaderIdentity.get_or_create_for_user(self.request.user)
        return kwargs

    @transaction.atomic
    def form_valid(self, form):
        instance = form.save()
        return redirect(instance)


class PackageDownloadView(View):
    def get(self, *args, **kwargs):
        owner = kwargs["owner"]
        name = kwargs["name"]
        version = kwargs["version"]

        package = get_object_or_404(Package, owner__name=owner, name=name)
        version = get_object_or_404(
            PackageVersion, package=package, version_number=version
        )
        version.maybe_increase_download_counter(self.request)
        return redirect(self.request.build_absolute_uri(version.file.url))
