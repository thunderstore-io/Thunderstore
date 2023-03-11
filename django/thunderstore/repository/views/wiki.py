from typing import Optional

from django.http import Http404, HttpResponse
from django.middleware import csrf
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import DetailView

from thunderstore.community.models import PackageListing
from thunderstore.repository.mixins import CommunityMixin
from thunderstore.repository.models import Package
from thunderstore.repository.models.wiki import PackageWiki
from thunderstore.repository.views.mixins import PackageTabsMixin
from thunderstore.repository.views.repository import get_package_listing_or_404


class PackageWikiBaseView(CommunityMixin, PackageTabsMixin, DetailView):
    model = PackageListing
    object: Optional[PackageListing]

    def get_wiki(self, package: Package) -> Optional[PackageWiki]:
        return PackageWiki.get_for_package(package, False)

    def get_object(self, *args, **kwargs) -> PackageListing:
        listing = get_package_listing_or_404(
            namespace=self.kwargs["owner"],
            name=self.kwargs["name"],
            community=self.community,
        )
        if not listing.can_be_viewed_by_user(self.request.user):
            raise Http404("Package is waiting for approval or has been rejected")
        return listing

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        package_listing = context["object"]
        context["wiki"] = self.get_wiki(package_listing.package)
        context.update(**self.get_tab_context(package_listing, "wiki"))
        return context


@method_decorator(ensure_csrf_cookie, name="dispatch")
class PackageWikiPageEditView(PackageWikiBaseView):
    template_name = "repository/package_wiki_edit.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        is_new = "page" not in self.kwargs
        context["is_new"] = is_new
        context["title"] = "New Page" if is_new else "Edit Page"
        context["editor_props"] = {
            "title": context["title"],
            "csrfToken": csrf.get_token(self.request),
        }
        return context


class PackageWikiHomeView(PackageWikiBaseView):
    template_name = "repository/package_wiki_home.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        return context


class PackageWikiPageDetailView(PackageWikiBaseView):
    template_name = "repository/package_wiki_detail.html"

    def get(self, *args, **kwargs) -> HttpResponse:
        # TODO: Redirect to correct URL if slug is wrong
        return super().get(*args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["page"] = {
            "title": "Page title placeholder",
            "markdown_content": "# Page content placeholder\n\nthis is a test markdown",
        }
        return context
