from django.contrib.auth import get_user_model
from django.db import transaction
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView
from django.views.generic import View

from repository.models import Package
from repository.models import PackageVersion
from repository.ziptools import PackageVersionForm

from django.shortcuts import redirect, get_object_or_404

MODS_PER_PAGE = 20


class PackageListView(ListView):
    model = Package
    paginate_by = MODS_PER_PAGE

    def get_queryset(self, *args, **kwargs):
        return (
            self.model.objects
            .filter(is_active=True)
            .prefetch_related("versions")
            .order_by("-is_pinned", "-date_updated")
        )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["page_title"] = f"All mods"
        return context


class PackageListByOwnerView(ListView):
    model = Package
    paginate_by = MODS_PER_PAGE

    def cache_owner(self):
        self.owner = get_object_or_404(
            get_user_model(),
            username=self.kwargs["owner"]
        )

    def dispatch(self, *args, **kwargs):
        self.cache_owner()
        return super().dispatch(*args, **kwargs)

    def get_queryset(self, *args, **kwargs):
        return (
            self.model.objects
            .filter(is_active=True, owner=self.owner)
            .prefetch_related("versions")
            .order_by("-is_pinned", "-date_updated")
        )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["page_title"] = f"Mods uploaded by {self.owner.username}"
        return context


class PackageListByDependencyView(ListView):
    model = Package
    paginate_by = MODS_PER_PAGE

    def cache_package(self):
        owner = self.kwargs["owner"]
        owner = get_object_or_404(get_user_model(), username=owner)
        name = self.kwargs["name"]
        package = get_object_or_404(
            self.model,
            is_active=True,
            owner=owner,
            name=name,
        )
        self.package = package

    def dispatch(self, *args, **kwargs):
        self.cache_package()
        return super().dispatch(*args, **kwargs)

    def get_queryset(self, *args, **kwargs):
        return (
            self.package.dependants
            .filter(is_active=True)
            .prefetch_related("versions")
            .order_by("-is_pinned", "-date_updated")
        )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["page_title"] = f"Mods that depend on {self.package.display_name}"
        return context


class PackageDetailView(DetailView):
    model = Package

    def get_object(self, *args, **kwargs):
        owner = self.kwargs["owner"]
        owner = get_object_or_404(get_user_model(), username=owner)
        name = self.kwargs["name"]
        return get_object_or_404(
            self.model,
            is_active=True,
            owner=owner,
            name=name,
        )

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
        kwargs["user"] = self.request.user
        return kwargs

    @transaction.atomic
    def form_valid(self, form):
        instance = form.save()
        instance.announce_release()
        instance.package.refresh_update_date()
        return redirect(form.instance)


class PackageDownloadView(View):

    def get(self, *args, **kwargs):
        owner = kwargs["owner"]
        name = kwargs["name"]
        version = kwargs["version"]

        package = get_object_or_404(Package, owner__username=owner, name=name)
        version = get_object_or_404(PackageVersion, package=package, version_number=version)
        version.maybe_increase_download_counter(self.request)
        return redirect(self.request.build_absolute_uri(version.file.url))
