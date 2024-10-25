from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import DetailView

from thunderstore.community.models import PackageListing
from thunderstore.frontend.url_reverse import get_community_url_reverse_args
from thunderstore.repository.mixins import CommunityMixin
from thunderstore.repository.models import PackageVersion


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PackageVersionDetailView(CommunityMixin, DetailView):
    model = PackageVersion

    def get_object(self, *args, **kwargs):
        owner = self.kwargs["owner"]
        name = self.kwargs["name"]
        version_number = self.kwargs["version"]
        listing = get_object_or_404(
            PackageListing,
            package__owner__name=owner,
            package__name=name,
            community=self.community,
        )
        if not listing.can_be_viewed_by_user(self.request.user):
            raise Http404("Package is waiting for approval or has been rejected")
        if not listing.package.is_active:
            raise Http404("Main package is deactivated")
        version = get_object_or_404(
            PackageVersion,
            package=listing.package,
            version_number=version_number,
        )
        if not version.can_be_viewed_by_user(self.request.user, listing.community):
            raise Http404("Package is waiting for approval or has been rejected")
        return version

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["owner_url"] = reverse_lazy(
            **get_community_url_reverse_args(
                community=self.community,
                viewname="packages.list_by_owner",
                kwargs={"owner": self.kwargs["owner"]},
            )
        )
        context["package_url"] = reverse_lazy(
            **get_community_url_reverse_args(
                community=self.community,
                viewname="packages.detail",
                kwargs={"owner": self.kwargs["owner"], "name": self.kwargs["name"]},
            )
        )
        return context
