from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from thunderstore.repository.factories import PackageVersionFactory
from thunderstore.repository.models import Package, PackageVersion, Team


class Command(BaseCommand):
    help = "Fills the database with test data"

    def add_arguments(self, parser):
        parser.add_argument("count", type=int, default=10)
        parser.add_argument("--clear", default=False, action="store_true")

    def handle(self, *args, **kwargs):
        if not settings.DEBUG:
            raise CommandError("Only executable in debug environments")
        if kwargs.get("clear", False):
            self.clear()
        self.create_data(kwargs.get("count", 10))

    def clear(self):
        print("Deleting existing package versions...")
        PackageVersion.objects.all().delete()
        print("Deleting existing packages...")
        Package.objects.all().delete()
        print("Deleting existing teams...")
        Team.objects.all().delete()

    def create_data(self, count):
        print("Creating teams...")

        last = 0
        last_team = Team.objects.order_by("-pk").first()
        if last_team:
            last = last_team.pk

        teams = [
            Team.objects.create(name=f"Test_Team_{last + i}") for i in range(count)
        ]
        print("Creating packages...")
        packages = [
            Package.objects.create(
                owner=teams[i],
                name=f"Test_Package_{i}",
            )
            for i in range(count)
        ]
        print("Creating package versions...")
        for i, package in enumerate(packages):
            for vernum in range(3):
                PackageVersionFactory.create(
                    package=package,
                    name=package.name,
                    version_number=f"{vernum}.0.0",
                    website_url="https://example.org",
                    description=f"Example mod {i}",
                    readme=f"# This is an example mod number {i}",
                )

        print("Linking dependencies...")
        dependency_count = int(count * 0.2)
        dependencies = [x.latest.id for x in Package.objects.all()[:dependency_count]]
        dependants = Package.objects.all()[dependency_count:]
        for package in dependants:
            package.latest.dependencies.set(dependencies)

        print("Done!")
