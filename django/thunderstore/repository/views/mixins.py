import dataclasses
from typing import List, Literal, TypedDict, Union

from thunderstore.community.models import PackageListing

TabName = Union[Literal["details"], Literal["wiki"]]


@dataclasses.dataclass
class Tab:
    title: str
    name: TabName
    url: str


class TabContext(TypedDict):
    tabs: List[Tab]
    active_tab: TabName


class PackageTabsMixin:
    def get_tab_context(
        self, listing: PackageListing, active_tab: TabName
    ) -> TabContext:
        return {
            "tabs": [
                Tab(title="Details", name="details", url=listing.get_absolute_url()),
                Tab(title="Wiki", name="wiki", url=listing.get_wiki_url()),
            ],
            "active_tab": active_tab,
        }
