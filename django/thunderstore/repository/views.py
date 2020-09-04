from django.db import transaction
from django.db.models import Q, Sum, Count
from django.http import Http404
from django.urls import reverse_lazy
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView
from django.views.generic import View

from thunderstore.community.models import PackageCategory
from thunderstore.repository.models import Package
from thunderstore.repository.models import PackageVersion
from thunderstore.repository.models import UploaderIdentity
from thunderstore.repository.package_upload import PackageUploadForm

from django.shortcuts import redirect, get_object_or_404

# Should be divisible by 4 and 3
MODS_PER_PAGE = 24


class PackageListSearchView(ListView):
    model = Package
    paginate_by = MODS_PER_PAGE

    def get_base_queryset(self):
        return self.model.objects.active()

    def get_page_title(self):
        return ""

    def get_cache_vary(self):
        return ""

    def get_categories(self):
        return PackageCategory.objects.all()

    def get_full_cache_vary(self):
        cache_vary = self.get_cache_vary()
        cache_vary += f".{self.get_search_query()}"
        cache_vary += f".{self.get_active_ordering()}"
        cache_vary += f".{self.get_selected_categories()}"
        cache_vary += f".{self.get_is_deprecated_included()}"
        cache_vary += f".{self.get_is_nsfw_included()}"
        return cache_vary

    def get_ordering_choices(self):
        return (
            ("last-updated", "Last updated"),
            ("newest", "Newest"),
            ("most-downloaded", "Most downloaded"),
            ("top-rated", "Top rated"),
        )

    def get_selected_categories(self):
        selections = self.request.GET.getlist("categories", [])
        result = []
        for selection in selections:
            try:
                result.append(int(selection))
            except ValueError:
                pass
        return result

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
            return queryset.order_by("-is_pinned", "is_deprecated", "-date_created")
        if active_ordering == "most-downloaded":
            return (
                queryset
                .annotate(total_downloads=Sum("versions__downloads"))
                .order_by("-is_pinned", "is_deprecated", "-total_downloads")
            )
        if active_ordering == "top-rated":
            return (
                queryset
                .annotate(total_rating=Count("package_ratings"))
                .order_by("-is_pinned", "is_deprecated", "-total_rating")
            )
        return queryset.order_by("-is_pinned", "is_deprecated", "-date_updated")

    def perform_search(self, queryset, search_query):
        search_fields = ("name", "owner__name", "latest__description")

        icontains_query = Q()
        parts = search_query.split(" ")
        for part in parts:
            for field in search_fields:
                icontains_query &= ~Q(**{
                    f"{field}__icontains": part
                })

        return (
            queryset
            .exclude(icontains_query)
            .distinct()
        )

    def get_queryset(self):
        queryset = (
            self.get_base_queryset()
            .prefetch_related("versions")
            .select_related(
                "latest",
                "owner",
            )
        )
        selected_categories = self.get_selected_categories()
        if selected_categories:
            category_queryset = Q()
            for category in selected_categories:
                category_queryset &= Q(package_listings__categories=category)
            queryset = queryset.exclude(~category_queryset)
        if not self.get_is_nsfw_included():
            queryset = queryset.exclude(package_listings__has_nsfw_content=True)
        if not self.get_is_deprecated_included():
            queryset = queryset.exclude(is_deprecated=True)
        search_query = self.get_search_query()
        if search_query:
            queryset = self.perform_search(queryset, search_query)
        return self.order_queryset(queryset)

    def get_breadcrumbs(self):
        return [{
            "url": reverse_lazy("packages.list"),
            "name": "Packages",
        }]

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["categories"] = self.get_categories()
        context["selected_categories"] = self.get_selected_categories()
        context["nsfw_included"] = self.get_is_nsfw_included()
        context["deprecated_included"] = self.get_is_deprecated_included()
        context["cache_vary"] = self.get_full_cache_vary()
        context["page_title"] = self.get_page_title()
        context["ordering_modes"] = self.get_ordering_choices()
        context["active_ordering"] = self.get_active_ordering()
        context["current_search"] = self.get_search_query()
        breadcrumbs = self.get_breadcrumbs()
        if len(breadcrumbs) > 1:
            context["breadcrumbs"] = breadcrumbs
        return context


class PackageListView(PackageListSearchView):

    def get_page_title(self):
        return f"All mods"

    def get_cache_vary(self):
        return "all"


class PackageListByOwnerView(PackageListSearchView):

    def get_breadcrumbs(self):
        breadcrumbs = super().get_breadcrumbs()
        return breadcrumbs + [{
            "url": reverse_lazy("packages.list_by_owner", kwargs=self.kwargs),
            "name": self.owner.name,
        }]

    def cache_owner(self):
        self.owner = get_object_or_404(
            UploaderIdentity,
            name=self.kwargs["owner"]
        )

    def dispatch(self, *args, **kwargs):
        self.cache_owner()
        return super().dispatch(*args, **kwargs)

    def get_base_queryset(self):
        return self.model.objects.active().exclude(~Q(owner=self.owner))

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
        package = (
            self.model.objects.active()
            .filter(owner=owner, name=name)
            .first()
        )
        if not package:
            raise Http404("No matching package found")
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
        package = (
            self.model.objects.active()
            .filter(owner=owner, name=name)
            .first()
        )
        if not package:
            raise Http404("No matching package found")
        return package

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        dependants_string = ""
        package = context["object"]
        dependant_count = package.dependants.active().count()

        if dependant_count == 1:
            dependants_string = f"{dependant_count} other mod depends on this mod"
        else:
            dependants_string = f"{dependant_count} other mods depend on this mod"

        context["dependants_string"] = dependants_string
        return context


class PackageVersionDetailView(DetailView):
    model = PackageVersion

    def get_object(self):
        owner = self.kwargs["owner"]
        name = self.kwargs["name"]
        version = self.kwargs["version"]
        package = get_object_or_404(Package, owner__name=owner, name=name)
        version = get_object_or_404(PackageVersion, package=package, version_number=version)
        return version


class PackageCreateView(CreateView):
    model = PackageVersion
    form_class = PackageUploadForm
    template_name = "repository/package_create.html"

    def dispatch(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return redirect("index")
        return super(PackageCreateView, self).dispatch(*args, **kwargs)

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super(PackageCreateView, self).get_form_kwargs(*args, **kwargs)
        kwargs["user"] = self.request.user
        kwargs["identity"] = UploaderIdentity.get_or_create_for_user(
            self.request.user
        )
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
        version = get_object_or_404(PackageVersion, package=package, version_number=version)
        version.maybe_increase_download_counter(self.request)
        return redirect(self.request.build_absolute_uri(version.file.url))
