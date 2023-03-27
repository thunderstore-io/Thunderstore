from typing import Dict, List, Optional, OrderedDict, Type

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from thunderstore.core.management.commands.content.base import (
    ContentPopulator,
    ContentPopulatorContext,
)
from thunderstore.core.management.commands.content.community import CommunityPopulator
from thunderstore.core.management.commands.content.community_site import (
    CommunitySitePopulator,
)
from thunderstore.core.management.commands.content.contract import (
    LegalContractPopulator,
)
from thunderstore.core.management.commands.content.contract_version import (
    LegalContractVersionPopulator,
)
from thunderstore.core.management.commands.content.dependencies import (
    DependencyPopulator,
)
from thunderstore.core.management.commands.content.package import PackagePopulator
from thunderstore.core.management.commands.content.package_listing import (
    ListingPopulator,
)
from thunderstore.core.management.commands.content.package_version import (
    PackageVersionPopulator,
)
from thunderstore.core.management.commands.content.package_wiki import (
    PackageWikiPopulator,
)
from thunderstore.core.management.commands.content.package_wiki_pages import (
    PackageWikiPagePopulator,
)
from thunderstore.core.management.commands.content.team import TeamPopulator

# In generation order; clearing order is inverted
CONTENT_POPULATORS: Dict[str, Type[ContentPopulator]] = OrderedDict[
    str, ContentPopulator
](
    [
        ("community", CommunityPopulator),
        ("community_site", CommunitySitePopulator),
        ("team", TeamPopulator),
        ("package", PackagePopulator),
        ("version", PackageVersionPopulator),
        ("dependency", DependencyPopulator),
        ("listing", ListingPopulator),
        ("contract", LegalContractPopulator),
        ("contract_version", LegalContractVersionPopulator),
        ("package_wiki", PackageWikiPopulator),
        ("package_wiki_pages", PackageWikiPagePopulator),
    ]
)


class Command(BaseCommand):
    help = "Fills the database with test data"
    disabled_handlers: Optional[List[str]] = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_arguments(self, parser) -> None:
        parser.add_argument("--community-count", type=int, default=20)
        parser.add_argument("--team-count", type=int, default=10)
        parser.add_argument("--package-count", type=int, default=1)
        parser.add_argument("--wiki-page-count", type=int, default=7)
        parser.add_argument("--version-count", type=int, default=3)
        parser.add_argument("--contract-count", type=int, default=3)
        parser.add_argument("--contract-version-count", type=int, default=8)
        parser.add_argument("--dependency-count", type=int, default=20)
        parser.add_argument("--clear", default=False, action="store_true")
        parser.add_argument(
            "--only",
            type=str,
            default=None,
            help=(
                "A comma separated list of content types to populate. Supports "
                f"{','.join(CONTENT_POPULATORS.keys())}."
            ),
        )

    def save_content_type_filter(self, only: str) -> None:
        content_types = only.split(",")
        if not all([x in CONTENT_POPULATORS.keys() for x in content_types]):
            options = ",".join(CONTENT_POPULATORS.keys())
            raise CommandError(
                f"Invalid --only selection provided, options are: {options}"
            )
        self.disabled_handlers = [
            key for key in CONTENT_POPULATORS.keys() if key not in content_types
        ]

    def clear(self) -> None:
        print("Clearing content")
        for key in reversed(CONTENT_POPULATORS.keys()):
            if key in self.disabled_handlers:
                continue
            handler = CONTENT_POPULATORS[key]()
            handler.clear()
        print("Done!")

    def populate(self, context: ContentPopulatorContext) -> None:
        print("Populating content")
        for key in CONTENT_POPULATORS.keys():
            handler = CONTENT_POPULATORS[key]()
            if key not in self.disabled_handlers:
                handler.populate(context)
            handler.update_context(context)
        print("Done!")

    def handle(self, *args, **kwargs) -> None:
        if not settings.DEBUG:
            raise CommandError("Only executable in debug environments")

        if only := kwargs.get("only"):
            self.save_content_type_filter(only)

        if kwargs.get("clear", False):
            self.clear()

        context = ContentPopulatorContext(
            package_count=kwargs.get("package_count", 0),
            version_count=kwargs.get("version_count", 0),
            team_count=kwargs.get("team_count", 0),
            dependency_count=kwargs.get("dependency_count", 0),
            community_count=kwargs.get("community_count", 0),
            contract_count=kwargs.get("contract_count", 0),
            contract_version_count=kwargs.get("contract_version_count", 0),
            wiki_page_count=kwargs.get("wiki_page_count", 0),
        )
        self.populate(context)
