from abc import ABC
from dataclasses import dataclass, field
from typing import Collection, Dict, List, Optional, OrderedDict, Type

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import signals

from thunderstore.community.models import Community, PackageListing
from thunderstore.repository.factories import PackageVersionFactory
from thunderstore.repository.models import Namespace, Package, PackageVersion, Team
from thunderstore.utils.iterators import print_progress


@dataclass
class ContentPopulatorContext:
    teams: Collection[Team] = field(default_factory=list)
    packages: Collection[Package] = field(default_factory=list)
    communities: Collection[Community] = field(default_factory=list)

    dependency_count: int = 0
    version_count: int = 0
    team_count: int = 0
    package_count: int = 0


class ContentPopulator(ABC):
    def populate(self, context: ContentPopulatorContext) -> None:
        ...

    def update_context(self, context) -> None:
        ...

    def clear(self) -> None:
        ...


class TeamPopulator(ContentPopulator):
    teams: Optional[List[Team]] = None
    name_prefix = "Test_Team_"

    def populate(self, context: ContentPopulatorContext) -> None:
        print("Populating teams...")

        last = 0
        last_team = Team.objects.order_by("-pk").first()
        if last_team:
            last = last_team.pk

        existing = list(
            Team.objects.filter(name__startswith=self.name_prefix)[: context.team_count]
        )
        remainder = context.team_count - len(existing)

        self.teams = existing + [
            Team.create(name=f"{self.name_prefix}{last + i}")
            for i in print_progress(range(remainder), remainder)
        ]

    def update_context(self, context) -> None:
        if self.teams is not None:
            context.teams = self.teams
        else:
            context.teams = Team.objects.filter(name__startswith=self.name_prefix)[
                : context.team_count
            ]

    def clear(self) -> None:
        print("Deleting existing teams...")
        Team.objects.all().delete()
        print("Deleting existing namespaces...")
        Namespace.objects.all().delete()


class PackagePopulator(ContentPopulator):
    packages: Optional[Collection[Package]] = None
    name_prefix = "Test_Package_"

    def populate(self, context: ContentPopulatorContext) -> None:
        print("Populating packages...")
        packages = []

        # Disabling signals to avoid spamming cache clear calls
        # TODO: Implement a context manager for disabling cache refresh instead
        signals.post_save.disconnect(Package.post_save, sender=Package)
        signals.post_delete.disconnect(Package.post_delete, sender=Package)

        for team in print_progress(context.teams, len(context.teams)):
            existing = list(
                team.owned_packages.filter(name__startswith=self.name_prefix)[
                    : context.package_count
                ]
            )
            offset = len(existing)
            remainder = context.package_count - offset
            team_packages = [
                Package.objects.create(
                    owner=team,
                    name=f"{self.name_prefix}{i + offset}",
                    namespace=team.get_namespace(),
                )
                for i in range(remainder)
            ]
            packages += team_packages

        # Re-enabling previously disabled signals
        signals.post_save.connect(Package.post_save, sender=Package)
        signals.post_delete.connect(Package.post_delete, sender=Package)

        self.packages = packages

    def update_context(self, context) -> None:
        if self.packages:
            context.packages = self.packages
        else:
            context.packages = Package.objects.filter(
                owner__in=context.teams,
                name__startswith=self.name_prefix,
            )

    def clear(self) -> None:
        print("Deleting existing packages...")
        Package.objects.all().delete()


class PackageVersionPopulator(ContentPopulator):
    def populate(self, context: ContentPopulatorContext) -> None:
        print("Populating package versions...")

        # Disabling signals to avoid spamming cache clear calls and other
        # needless action
        # TODO: Implement a context manager for disabling cache refresh instead
        signals.post_save.disconnect(PackageVersion.post_save, sender=PackageVersion)
        signals.post_delete.disconnect(
            PackageVersion.post_delete, sender=PackageVersion
        )
        signals.post_save.disconnect(Package.post_save, sender=Package)
        signals.post_delete.disconnect(Package.post_delete, sender=Package)

        for i, package in print_progress(
            enumerate(context.packages), len(context.packages)
        ):
            vercount = package.versions.count()
            for vernum in range(context.version_count - vercount):
                PackageVersionFactory.create(
                    package=package,
                    name=package.name,
                    version_number=f"{vernum + vercount}.0.0",
                    website_url="https://example.org",
                    description=f"Example mod {i}",
                    readme=f"# This is an example mod number {i}",
                    changelog=f"# Example changelog for mod number {i}",
                )

            # Manually calling would-be signals once per package, as it doesn't
            # actually make use of the sender param at all (and can be None)
            package.handle_created_version(None)
            package.handle_updated_version(None)

        # Re-enabling previously disabled signals
        signals.post_save.connect(PackageVersion.post_save, sender=PackageVersion)
        signals.post_delete.connect(PackageVersion.post_delete, sender=PackageVersion)
        signals.post_save.connect(Package.post_save, sender=Package)
        signals.post_delete.connect(Package.post_delete, sender=Package)

    def clear(self) -> None:
        print("Deleting existing package versions...")
        PackageVersion.objects.all().delete()


class DependencyPopulator(ContentPopulator):
    def populate(self, context: ContentPopulatorContext) -> None:
        print("Linking dependencies...")
        dependencies = [
            x.latest.id for x in context.packages[: context.dependency_count]
        ]
        dependants = context.packages[context.dependency_count :]
        for package in print_progress(dependants, len(dependants)):
            package.latest.dependencies.set(dependencies)

    def clear(self) -> None:
        print("Deleting existing package dependency relations")
        PackageVersion.dependencies.through.objects.all().delete()


class ListingPopulator(ContentPopulator):
    def populate(self, context: ContentPopulatorContext) -> None:
        print("Populating package listings")

        # Disabling signals to avoid spamming cache clear calls
        # TODO: Implement a context manager for disabling cache refresh instead
        signals.post_save.disconnect(PackageListing.post_save, sender=PackageListing)
        signals.post_delete.disconnect(
            PackageListing.post_delete, sender=PackageListing
        )

        for i, package in print_progress(
            enumerate(context.packages), len(context.packages)
        ):
            for community in context.communities:
                package.get_or_create_package_listing(community)

        # Re-enabling previously disabled signals
        signals.post_save.connect(PackageListing.post_save, sender=PackageListing)
        signals.post_delete.connect(PackageListing.post_delete, sender=PackageListing)

    def clear(self) -> None:
        print("Deleting existing package listings...")
        PackageListing.objects.all().delete()


# In generation order; clearing order is inverted
CONTENT_POPULATORS: Dict[str, Type[ContentPopulator]] = OrderedDict[
    str, ContentPopulator
](
    [
        ("team", TeamPopulator),
        ("package", PackagePopulator),
        ("version", PackageVersionPopulator),
        ("dependency", DependencyPopulator),
        ("listing", ListingPopulator),
    ]
)


class Command(BaseCommand):
    help = "Fills the database with test data"
    disabled_handlers: Optional[List[str]] = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_arguments(self, parser) -> None:
        parser.add_argument("--team-count", type=int, default=10)
        parser.add_argument("--package-count", type=int, default=1)
        parser.add_argument("--version-count", type=int, default=3)
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
            communities=Community.objects.all()[:1],
        )
        self.populate(context)
