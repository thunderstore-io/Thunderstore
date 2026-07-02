from typing import List, Tuple

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.management import BaseCommand, CommandError, call_command

from thunderstore.community.models import (
    Community,
    CommunityNotification,
    CommunitySite,
)

# Domains the local stack answers on. `thunderstore.localhost` is the primary
# host (served by the cyberstorm-remix app via nginx) and `old.thunderstore.localhost`
# mirrors the legacy Django-rendered site, matching the production split where the
# old site lives under an `old.` subdomain.
SITE_DEFINITIONS: List[Tuple[str, str]] = [
    ("thunderstore.localhost", "Thunderstore"),
    ("old.thunderstore.localhost", "Thunderstore (legacy)"),
    ("auth.thunderstore.localhost", "Thunderstore Auth"),
]

# Hosts that should resolve to a community when hit through the legacy
# host-based community routing.
COMMUNITY_SITE_DOMAINS: List[str] = [
    "thunderstore.localhost",
    "old.thunderstore.localhost",
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

        # Demo community notifications, shown at the top of the community's
        # package list on the frontend (thunderstore.localhost is bound to this
        # community below). Covers all severities plus an internal (SPA) and an
        # external link.
        self.stdout.write("Adding demo community notifications...")
        CommunityNotification.objects.update_or_create(
            community=community,
            defaults={
                "notifications": [
                    {
                        "type": "critical",
                        "content": (
                            "Scheduled maintenance is ongoing. See the "
                            "[status page](https://status.thunderstore.io) for "
                            "updates."
                        ),
                    },
                    {
                        "type": "warning",
                        "content": (
                            "Some packages are being re-indexed and may be "
                            "temporarily missing from the list."
                        ),
                    },
                    {
                        "type": "info",
                        "content": (
                            "New to modding? Browse [all communities]"
                            "(/communities/) to discover more games."
                        ),
                    },
                ]
            },
        )

        for domain, name in SITE_DEFINITIONS:
            Site.objects.update_or_create(
                domain=domain,
                defaults={"name": name},
            )

        # Ensure only the defined sites exist
        Site.objects.exclude(domain__in=[s[0] for s in SITE_DEFINITIONS]).delete()
        CommunitySite.objects.all().delete()

        # Bind the relevant hosts to the community so legacy host-based routing
        # resolves on both the primary and the legacy domain.
        for domain in COMMUNITY_SITE_DOMAINS:
            site = Site.objects.get(domain=domain)
            CommunitySite.objects.create(site=site, community=community)

        User = get_user_model()
        if not User.objects.filter(username="admin").exists():
            self.stdout.write("Creating superuser 'admin'...")
            User.objects.create_superuser("admin", "admin@example.com", "admin")
        else:
            self.stdout.write("Superuser 'admin' already exists.")

        self.stdout.write(self.style.SUCCESS("Local development environment ready."))
