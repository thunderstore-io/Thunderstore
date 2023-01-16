import requests
from django.conf import settings
from django.db import transaction

from thunderstore.community.models import (
    Community,
    PackageCategory,
    PackageListingSection,
)
from thunderstore.schema_import.schema import Schema, SchemaCommunity


# TODO: Add support for deleting or at least disabling unnecessary content
@transaction.atomic
def import_community(identifier: str, schema: SchemaCommunity):
    if not (community := Community.objects.filter(identifier=identifier).first()):
        community = Community(
            identifier=identifier,
            is_listed=False,
            block_auto_updates=False,
        )

    if community.block_auto_updates:
        return

    community.slogan = f"The {schema.display_name} Mod Database"
    community.description = (
        "Thunderstore is a mod database and API for downloading mods"
    )
    community.name = schema.display_name
    community.discord_url = schema.discord_url
    community.wiki_url = schema.wiki_url
    community.save()

    for k, v in schema.categories.items():
        if not (
            category := PackageCategory.objects.filter(
                slug=k, community=community
            ).first()
        ):
            category = PackageCategory(slug=k, community=community)
        category.name = v.label
        category.save()

    for index, (k, v) in enumerate(schema.sections.items()):
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


def import_schema_communities(schema: Schema):
    for identifier, community in schema.communities.items():
        import_community(identifier, community)


def sync_thunderstore_schema():
    response = requests.get(
        settings.ECOSYSTEM_SCHEMA_URL, headers={"accept-encoding": "gzip"}
    )
    schema = Schema.parse_obj(response.json())
    import_schema_communities(schema)
