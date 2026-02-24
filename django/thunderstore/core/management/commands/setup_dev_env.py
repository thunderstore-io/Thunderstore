from typing import List, Tuple

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.management import BaseCommand, CommandError, call_command

from thunderstore.community.models import Community, CommunitySite

SITE_DEFINITIONS: List[Tuple[str, str]] = [
    ("thunderstore.localhost", "Thunderstore"),
    ("auth.thunderstore.localhost", "Thunderstore Auth"),
]


class Command(BaseCommand):
    help = "Prepares a local development environment with test data and site mappings"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--skip-test-data",
            action="store_true",
            help="Reuse existing database contents instead of re-populating test data.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("setup_dev_env can only run when DEBUG=True")

        self.stdout.write("Running migrations...")
        call_command("migrate")

        if not options["skip_test_data"]:
            self.stdout.write("Populating test data...")
            call_command("create_test_data", "--clear", "--reuse-icon")

        self.stdout.write("Creating Risk of Rain 2 community...")
        community, _ = Community.objects.get_or_create(
            identifier="riskofrain2",
            defaults={"name": "Risk of Rain 2"},
        )

        for domain, name in SITE_DEFINITIONS:
            Site.objects.update_or_create(
                domain=domain,
                defaults={"name": name},
            )

        # Ensure only the defined sites exist
        Site.objects.exclude(domain__in=[s[0] for s in SITE_DEFINITIONS]).delete()
        CommunitySite.objects.all().delete()

        # Bind localhost to the community
        localhost = Site.objects.get(domain="thunderstore.localhost")
        CommunitySite.objects.create(site=localhost, community=community)

        User = get_user_model()
        if not User.objects.filter(username="admin").exists():
            self.stdout.write("Creating superuser 'admin'...")
            User.objects.create_superuser("admin", "admin@example.com", "admin")
        else:
            self.stdout.write("Superuser 'admin' already exists.")

        self.stdout.write(self.style.SUCCESS("Local development environment ready."))
