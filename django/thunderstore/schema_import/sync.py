import requests
from django.conf import settings
from django.db import transaction

from thunderstore.community.models import (
    Community,
    PackageCategory,
    PackageListingSection,
)
from thunderstore.schema_import.schema import Schema, SchemaGame


# TODO: Add support for deleting or at least disabling unnecessary content
@transaction.atomic
def import_game_community(identifier: str, game: SchemaGame):
    if not game.thunderstore:
        return

    config = game.thunderstore

    if not (community := Community.objects.filter(identifier=identifier).first()):
        community = Community(
            identifier=identifier,
            is_listed=False,
            block_auto_updates=False,
        )

    if community.block_auto_updates:
        return

    community.slogan = f"The {game.meta.displayName} Mod Database"
    community.description = (
        "Thunderstore is a mod database and API for downloading mods"
    )
    community.name = game.meta.displayName
    community.discord_url = config.discord_url
    community.wiki_url = config.wiki_url
    community.save()

    for k, v in config.categories.items():
        if not (
            category := PackageCategory.objects.filter(
                slug=k, community=community
            ).first()
        ):
            category = PackageCategory(slug=k, community=community)
        category.name = v.label
        category.save()

    for index, (k, v) in enumerate(config.sections.items()):
        if not (
            section := PackageListingSection.objects.filter(
                community=community, slug=k
            ).first()
        ):
            section = PackageListingSection(slug=k, community=community)
        section.name = v.name
        section.priority = -index
        section.is_listed = True
        section.save()
        section.require_categories.set(
            PackageCategory.objects.filter(
                slug__in=v.require_categories,
                community=community,
            )
        )
        section.exclude_categories.set(
            PackageCategory.objects.filter(
                slug__in=v.exclude_categories,
                community=community,
            )
        )


def import_schema_games(schema: Schema):
    for identifier, game in schema.games.items():
        import_game_community(identifier, game)


def sync_thunderstore_schema():
    response = requests.get(
        settings.ECOSYSTEM_SCHEMA_URL, headers={"accept-encoding": "gzip"}
    )
    schema = Schema.parse_obj(response.json())
    import_schema_games(schema)
