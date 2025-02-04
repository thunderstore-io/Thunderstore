# Scrape data from Thunderstore API to local database for testing
#
# Data is fetched from the ThunderStore public API as JSON data and
# written to the database via Django models.  Following models are
# populated:
#
#  * Community
#  * PackageCategory
#  * Team
#  * Package
#  * PackageVersion
#
# Icons or package files are not fetched nor stored in this script.

import time

import requests

from thunderstore.community.models import Community
from thunderstore.repository.models import Package, PackageVersion, Team

API_BASE_URL = "https://thunderstore.io"


def scrape_data_and_store_to_database(create_communities=True):
    if create_communities:
        community_data = fetch_community_data()
        communities = store_communities_and_categories_to_database(community_data)
    else:
        communities = Community.objects.all()
    count = len(communities)
    for n, community in enumerate(communities, 1):
        print("=============================================================")
        print(f"Processing Community {n}/{count} {community.name!r}...")
        json_data = get_data_from_public_api(community)
        store_packages_to_database(json_data, community)


def fetch_community_data():
    data = _get("api/experimental/community/")
    for community_data in data["results"]:
        identifier = community_data["identifier"]
        categ_data = _get(f"api/experimental/community/{identifier}/category/")
        community_data["categories"] = categ_data["results"]
    return data["results"]


def _get(url_path):
    url = f"{API_BASE_URL}/{url_path}"
    print(f"Fetching from {url}...", end=" ", flush=True)
    response = requests.get(url)
    response.raise_for_status()
    print(f"got {len(response.content):,d} bytes.")
    time.sleep(0.2)  # Be nice to the server & avoid rate limiting
    return response.json()


def store_communities_and_categories_to_database(communities_data):
    # Create a separate queryset to discard the select_related fields
    community_qs = Community.objects.all().select_related()
    communities = []
    for data in communities_data:
        print(f"Processing Community {data['name']!r}...")
        community = community_qs.update_or_create(
            identifier=data["identifier"],
            defaults=dict(
                name=data["name"],
                discord_url=data["discord_url"],
                wiki_url=data["wiki_url"],
                require_package_listing_approval=data[
                    "require_package_listing_approval"
                ],
            ),
        )[0]
        communities.append(community)
        for category_data in data["categories"]:
            community.package_categories.update_or_create(
                slug=category_data["slug"],
                community=community,
                defaults=dict(
                    name=category_data["name"],
                ),
            )
    return communities


def get_data_from_public_api(community):
    return _get(f"c/{community.identifier}/api/v1/package/")


def store_packages_to_database(data, community):
    category_map = {x.name: x for x in community.package_categories.all()}
    version_map = {
        (pkg_pk, ver): ver_pk
        for (pkg_pk, ver, ver_pk) in PackageVersion.objects.all().values_list(
            "package__pk", "version_number", "pk"
        )
    }
    for n, pkg_data in enumerate(data, 1):
        print(f"Processing Package {n}/{len(data)} {pkg_data['name']!r}...")
        team, namespace = get_or_create_team_and_ns(pkg_data["owner"])
        package, _pkg_created = Package.objects.update_or_create(
            owner=team,
            namespace=namespace,
            name=pkg_data["name"],
            defaults=dict(
                date_created=pkg_data["date_created"],
                date_updated=pkg_data["date_updated"],
                uuid4=pkg_data["uuid4"],
                is_pinned=pkg_data["is_pinned"],
                is_deprecated=pkg_data["is_deprecated"],
            ),
        )
        package.update_listing(
            has_nsfw_content=pkg_data["has_nsfw_content"],
            categories=[category_map[x] for x in pkg_data["categories"]],
            community=community,
        )
        new_versions = []
        existing_versions = []
        for ver_data in pkg_data["versions"]:
            key = (package.pk, ver_data["version_number"])
            existing_pk = version_map.get(key)
            if existing_pk:
                existing_versions.append((existing_pk, ver_data))
            else:
                new_versions.append(ver_data)
        if new_versions:
            print(f"  {len(new_versions)} new versions...")
            PackageVersion.objects.bulk_create(
                [
                    PackageVersion(
                        package=package,
                        name=ver_data["name"],
                        version_number=ver_data["version_number"],
                        description=ver_data["description"],
                        # icon=ver_data["icon"],
                        downloads=ver_data["downloads"],
                        date_created=ver_data["date_created"],
                        website_url=ver_data["website_url"],
                        is_active=ver_data["is_active"],
                        uuid4=ver_data["uuid4"],
                        file_size=ver_data["file_size"],
                    )
                    for ver_data in new_versions
                ]
            )
        if existing_versions:
            print(f"  {len(existing_versions)} existing versions...")
            PackageVersion.objects.bulk_update(
                [
                    PackageVersion(
                        pk=pk,
                        description=ver_data["description"],
                        # icon=ver_data["icon"],
                        downloads=ver_data["downloads"],
                        date_created=ver_data["date_created"],
                        website_url=ver_data["website_url"],
                        is_active=ver_data["is_active"],
                        file_size=ver_data["file_size"],
                    )
                    for pk, ver_data in existing_versions
                ],
                fields=[
                    "description",
                    "downloads",
                    "date_created",
                    "website_url",
                    "is_active",
                    "file_size",
                ],
            )


def get_or_create_team_and_ns(owner):
    team_and_ns = team_cache.get(owner)
    if not team_and_ns:
        team = Team.objects.filter(name=owner).first()
        if not team:
            if "-" in owner:
                # Handle special case of invalid characters in team name
                assert owner in {"sinai-dev"}, owner
                team = Team.create(name=owner.replace("-", "_"))
                team_qs = Team.objects.filter(pk=team.pk)
                team_qs.update(name=owner)
                team_qs[0].namespaces.update(name=owner)
            else:
                team = Team.create(name=owner)
        team_and_ns = (team, team.namespaces.first())
        team_cache[owner] = team_and_ns
    return team_and_ns


team_cache = {}
