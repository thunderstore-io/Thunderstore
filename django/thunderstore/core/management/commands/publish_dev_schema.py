import json
import re
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from thunderstore.community.models import Community
from thunderstore.repository.models import APIV1ChunkedPackageCache
from thunderstore.schema_server.models import SchemaChannel

CHANNEL = "dev"
IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9](-?[a-z0-9])*$")


def _game(community: Community) -> dict:
    identifier = community.identifier
    return {
        "uuid": str(
            uuid.uuid5(
                uuid.NAMESPACE_URL, f"https://thunderstore.localhost/c/{identifier}"
            )
        ),
        "label": identifier,
        "meta": {"displayName": community.name, "iconUrl": None},
        "distributions": [{"platform": "other"}],
        "r2modman": [
            {
                "meta": {"displayName": community.name, "iconUrl": None},
                "internalFolderName": identifier,
                "dataFolderName": identifier,
                "distributions": [{"platform": "other"}],
                "settingsIdentifier": identifier,
                "packageIndex": (
                    f"{settings.PROTOCOL}{settings.PRIMARY_HOST}"
                    f"/c/{identifier}/api/v1/package-listing-index/"
                ),
                "steamFolderName": identifier,
                "exeNames": [f"{identifier}.exe"],
                "gameInstanceType": "game",
                "gameSelectionDisplayMode": "visible",
                "additionalSearchStrings": [],
                "packageLoader": "bepinex",
                "installRules": [
                    {
                        "route": "BepInEx/plugins",
                        "defaultFileExtensions": [".dll"],
                        "trackingMethod": "subdir",
                        "subRoutes": [],
                        "isDefaultLocation": True,
                    }
                ],
                "relativeFileExclusions": None,
            }
        ],
    }


class Command(BaseCommand):
    help = "Publish a mod-manager schema for the local communities on the dev channel"

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("publish_dev_schema can only run when DEBUG=True")

        games = {}
        for community in Community.objects.order_by("identifier"):
            if not IDENTIFIER_PATTERN.match(community.identifier):
                self.stdout.write(
                    f"Skipping {community.identifier}: identifier is not a schema label"
                )
                continue
            games[community.identifier] = _game(community)

        if not games:
            raise CommandError("No communities to publish")

        schema = {
            "schemaVersion": "0.3.0",
            "games": games,
            "communities": {},
            "packageInstallers": {},
            "modloaderPackages": [],
        }
        content = json.dumps(schema).encode()

        User = get_user_model()
        user = (
            User.objects.filter(is_active=True).order_by("-is_superuser", "id").first()
        )
        if user is None:
            raise CommandError("No active user exists to own the dev schema channel")

        channel, _ = SchemaChannel.objects.get_or_create(identifier=CHANNEL)
        channel.authorized_users.add(user)
        SchemaChannel.update_channel(user, CHANNEL, content)

        self.stdout.write(
            self.style.SUCCESS(
                f"Published {len(games)} communities to schema channel '{CHANNEL}'."
            )
        )

        # A community is missing from the mod manager until this index exists.
        # Rebuild directly so a failure stops the command instead of being swallowed.
        self.stdout.write("Building package list caches...")
        for community in Community.objects.iterator():
            APIV1ChunkedPackageCache.update_for_community(community)
        APIV1ChunkedPackageCache.drop_stale_cache()
        self.stdout.write(self.style.SUCCESS("Package list caches updated."))
