import dataclasses
from typing import Dict, List, Optional, TypedDict

from django.http import Http404
from django.views.generic import DetailView

from thunderstore.community.models import PackageListing
from thunderstore.core.types import UserType
from thunderstore.plugins.registry import plugin_registry
from thunderstore.repository.mixins import CommunityMixin
from thunderstore.repository.views.package._utils import get_package_listing_or_404


@dataclasses.dataclass
class PartialTab:
    url: str
    title: str
    is_disabled: bool = False


@dataclasses.dataclass
class Tab:
    title: str
    name: str
    url: str
    is_disabled: bool
    is_active: bool


class TabContext(TypedDict):
    tabs: List[Tab]


class PackageTabsMixin:
    def get_tab_context(
        self,
        user: UserType,
        listing: PackageListing,
        active_tab: Optional[str],
    ) -> TabContext:
        tabs: Dict[str, PartialTab] = {
            **{
                "details": PartialTab(url=listing.get_absolute_url(), title="Details"),
                "versions": PartialTab(
                    url=listing.get_versions_url(), title="Versions"
                ),
                "changelog": PartialTab(
                    url=listing.get_changelog_url(),
                    title="Changelog",
                    is_disabled=not listing.package.changelog(),
                ),
                "wiki": PartialTab(
                    url=listing.get_wiki_url(),
                    title="Wiki",
                    is_disabled=(
                        not listing.package.has_wiki
                        and not listing.package.can_user_manage_wiki(user)
                    ),
                ),
            },
            **plugin_registry.get_package_tabs(user, listing),
        }
        return {
            "tabs": [
                Tab(
                    title=v.title,
                    name=k,
                    url=v.url,
                    is_disabled=v.is_disabled and k != active_tab,
                    is_active=k == active_tab,
                )
                for k, v in tabs.items()
            ],
        }


class PackageListingDetailView(CommunityMixin, PackageTabsMixin, DetailView):
    model = PackageListing
    object: Optional[PackageListing] = None
    tab_name: Optional[str] = None

    def get_tab_name(self) -> Optional[str]:
        return self.tab_name

    def get_object(self, queryset=None) -> PackageListing:
        if not self.object:
            listing = get_package_listing_or_404(
                namespace=self.kwargs["owner"],
                name=self.kwargs["name"],
                community=self.community,
            )
            if not listing.can_be_viewed_by_user(self.request.user):
                raise Http404("Package is waiting for approval or has been rejected")
            self.object = listing
        return self.object

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        package_listing = context["object"]
        context.update(
            **self.get_tab_context(
                self.request.user, package_listing, self.get_tab_name()
            )
        )
        return context
