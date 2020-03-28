from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from repository.factories import PackageVersionFactory
from repository.models import UploaderIdentity
from repository.models import Package


class Command(BaseCommand):
    help = "Fills the database with test data"

    def add_arguments(self, parser):
        parser.add_argument("count", type=int, default=10)

    def handle(self, *args, **kwargs):
        if not settings.DEBUG:
            raise CommandError("Only executable in debug environments")
        self.create_data(kwargs.get("count", 10))

    def create_data(self, count):
        print("Creating uploaders...")
        last = UploaderIdentity.objects.order_by("-pk").first().pk
        uploaders = [
            UploaderIdentity.objects.create(name=f"Test-Identity-{last + i}")
            for i in range(count)
        ]
        print("Creating packages...")
        packages = [
            Package.objects.create(
                owner=uploaders[i],
                name=f"Test_Package_{i}",
            )
            for i in range(count)
        ]
        print("Creating package versions...")
        for i, package in enumerate(packages):
            PackageVersionFactory.create(
                package=package,
                name=package.name,
                version_number="1.0.0",
                website_url="https://example.org",
                description=f"Example mod {i}",
                readme=f"# This is an example mod number {i}",
            )
        print("Done!")
