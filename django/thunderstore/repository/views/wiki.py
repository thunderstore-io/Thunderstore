from typing import Optional

from django.http import Http404, HttpResponse
from django.middleware import csrf
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import DetailView

from thunderstore.community.models import PackageListing
from thunderstore.frontend.url_reverse import get_community_url_reverse_args
from thunderstore.repository.mixins import CommunityMixin
from thunderstore.repository.models import Package
from thunderstore.repository.models.wiki import PackageWiki
from thunderstore.repository.views.mixins import PackageTabsMixin
from thunderstore.repository.views.repository import get_package_listing_or_404
from thunderstore.wiki.models import WikiPage


class PackageWikiBaseView(CommunityMixin, PackageTabsMixin, DetailView):
    model = PackageListing
    object: Optional[PackageListing] = None
    wiki: Optional[PackageWiki] = None

    def get_wiki(self, package: Package) -> Optional[PackageWiki]:
        if not self.wiki:
            self.wiki = PackageWiki.get_for_package(package, False)
        return self.wiki

    def get_object(self, *args, **kwargs) -> PackageListing:
        if not self.object:
            listing = get_package_listing_or_404(
                namespace=self.kwargs["owner"],
                name=self.kwargs["name"],
                community=self.community,
            )
            if not listing.can_be_viewed_by_user(self.request.user):
                raise Http404("Package is waiting for approval or has been rejected")
            return listing
        return self.object

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
    page: Optional[WikiPage] = None

    def get_page(self, wiki: PackageWiki) -> Optional[WikiPage]:
        if not self.page:
            self.page = WikiPage.objects.filter(
                pk=self.kwargs.get("page"),
                wiki__package_wiki=wiki,
            ).first()
        return self.page

    def get(self, *args, **kwargs) -> HttpResponse:
        page = self.get_page(self.get_wiki(self.get_object(*args, **kwargs).package))
        if self.kwargs.get("pslug", "") != page.slug:
            self.kwargs["pslug"] = page.slug
            return redirect(
                reverse(
                    **get_community_url_reverse_args(
                        community=self.community,
                        viewname="packages.detail.wiki.page.detail",
                        kwargs=self.kwargs,
                    )
                )
            )
        return super().get(*args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["page"] = self.get_page(context["wiki"])
        return context
