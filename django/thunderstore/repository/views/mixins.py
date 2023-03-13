import dataclasses
from typing import Dict, List, Literal, Set, TypedDict, Union

from thunderstore.community.models import PackageListing

TabName = Union[Literal["details"], Literal["wiki"]]


@dataclasses.dataclass
class PartialTab:
    url: str
    title: str


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
        listing: PackageListing,
        active_tab: TabName,
        disabled_tabs: Set[TabName],
    ) -> TabContext:
        tabs: Dict[TabName, PartialTab] = {
            "details": PartialTab(url=listing.get_absolute_url(), title="Details"),
            "wiki": PartialTab(url=listing.get_wiki_url(), title="Wiki"),
        }
        return {
            "tabs": [
                Tab(
                    title=v.title,
                    name=k,
                    url=v.url,
                    is_disabled=k in disabled_tabs,
                    is_active=k == active_tab,
                )
                for k, v in tabs.items()
            ],
        }
