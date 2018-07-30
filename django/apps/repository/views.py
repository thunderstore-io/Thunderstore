from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView
from django.views.generic import View

from repository.models import Package
from repository.models import PackageVersion
from repository.ziptools import PackageVersionForm

from django.shortcuts import redirect, get_object_or_404


class PackageListView(ListView):
    model = Package
    paginate_by = 50

    def get_queryset(self, *args, **kwargs):
        return self.model.objects.filter(is_active=True)


class PackageDetailView(DetailView):
    model = Package


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

    def form_valid(self, form):
        form.save()
        return redirect(form.instance)


class PackageDownloadView(View):

    def get(self, *args, **kwargs):
        owner = kwargs["owner"]
        name = kwargs["name"]
        version = kwargs["version"]

        package = get_object_or_404(Package, owner__username=owner, name=name)
        version = get_object_or_404(PackageVersion, package=package, version_number=version)
        version.downloads += 1
        version.save(update_fields=("downloads",))
        return redirect(self.request.build_absolute_uri(version.file.url))
