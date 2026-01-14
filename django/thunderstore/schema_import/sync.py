import requests
from django.conf import settings
from django.db import transaction
from django.db.models import Count

from thunderstore.community.models import (
    Community,
    PackageCategory,
    PackageListing,
    PackageListingSection,
)
from thunderstore.core.utils import ExceptionLogger
from thunderstore.repository.models import PackageInstaller
from thunderstore.repository.package_reference import PackageReference
from thunderstore.schema_import.schema import (
    Schema,
    SchemaCommunity,
    SchemaPackageInstaller,
)


def get_slogan_from_display_name(name: str) -> str:
    if name.lower().startswith("the "):
        slogan_name = name[4:]
    else:
        slogan_name = name
    return f"The {slogan_name} Mod Database"


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

    community.slogan = get_slogan_from_display_name(schema.display_name)
    community.short_description = schema.short_description
    community.description = (
        "Thunderstore is a mod database and API for downloading mods"
    )
    community.name = schema.display_name
    community.discord_url = schema.discord_url
    community.wiki_url = schema.wiki_url
    community.save()

    if schema.autolist_package_ids:
        for package_id in schema.autolist_package_ids:
            with ExceptionLogger(continue_on_error=True):
                package = PackageReference.parse(package_id).package
                if package is not None:
                    if package.get_package_listing(community) is None:
                        PackageListing.objects.create(
                            package=package,
                            community=community,
                            is_auto_imported=True,
                        )

    for k, v in schema.categories.items():
        if not (
            category := PackageCategory.objects.filter(
                slug=k, community=community
            ).first()
        ):
            category = PackageCategory(slug=k, community=community)
        category.name = v.label
        category.save()

    PackageCategory.objects.filter(
        community=community,
    ).exclude(
        slug__in=schema.categories.keys(),
    ).annotate(
        package_count=Count("packages"),
    ).filter(
        package_count=0,
    ).delete()

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

    PackageListingSection.objects.filter(
        community=community,
    ).exclude(
        slug__in=schema.sections.keys(),
    ).delete()


def import_schema_communities(schema: Schema):
    for identifier, community in schema.communities.items():
        with ExceptionLogger(continue_on_error=True):
            import_community(identifier, community)


@transaction.atomic
def import_installer(identifier: str, schema: SchemaPackageInstaller):
    if not (
        installer := PackageInstaller.objects.filter(identifier=identifier).first()
    ):
        installer = PackageInstaller(identifier=identifier)
    installer.name = schema.name
    installer.description = schema.description
    installer.save()


def import_schema_package_installers(schema: Schema):
    if schema.package_installers is None:
        return

    for identifier, installer in schema.package_installers.items():
        with ExceptionLogger(continue_on_error=True):
            import_installer(identifier, installer)


def sync_thunderstore_schema():
    response = requests.get(
        settings.ECOSYSTEM_SCHEMA_URL, headers={"accept-encoding": "gzip"}
    )
    schema = Schema.parse_obj(response.json())

    with ExceptionLogger(continue_on_error=True):
        import_schema_communities(schema)

    with ExceptionLogger(continue_on_error=True):
        import_schema_package_installers(schema)
