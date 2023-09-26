import dataclasses
from typing import Dict, List, Literal, TypedDict, Union

from thunderstore.community.models import PackageListing
from thunderstore.core.types import UserType
from thunderstore.plugins.registry import plugin_registry

TabName = Union[Literal["details"], Literal["wiki"]]


@dataclasses.dataclass
class PartialTab:
    url: str
    title: str
    is_disabled: bool = False


@dataclasses.dataclass
class Tab:
    title: str
    name: TabName
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
        active_tab: TabName,
    ) -> TabContext:
        tabs: Dict[TabName, PartialTab] = {
            **{
                "details": PartialTab(url=listing.get_absolute_url(), title="Details"),
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
