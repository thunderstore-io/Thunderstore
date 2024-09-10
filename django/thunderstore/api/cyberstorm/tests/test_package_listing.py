import json
from datetime import datetime
from typing import List, Optional

import pytest
from rest_framework.test import APIClient

from thunderstore.api.cyberstorm.views.package_listing import (
    DependencySerializer,
    get_custom_package_listing,
)
from thunderstore.community.factories import (
    CommunityFactory,
    PackageCategoryFactory,
    PackageListingFactory,
)
from thunderstore.community.models.package_category import PackageCategory
from thunderstore.community.models.package_listing import PackageListing
from thunderstore.repository.factories import (
    PackageRatingFactory,
    PackageVersionFactory,
    TeamMemberFactory,
)
from thunderstore.repository.models.team import TeamMember


@pytest.mark.django_db
def test_get_custom_package_listing__returns_objects_matching_args() -> None:
    expected = PackageListingFactory()
    PackageListingFactory(package_=expected.package)  # Different Community
    PackageListingFactory(
        community=expected.community,
        package_kwargs={"name": expected.package.name},
    )  # Different Namespace
    PackageListingFactory(
        community=expected.community,
        package_kwargs={"namespace": expected.package.namespace},
    )  # Different Package name

    actual = get_custom_package_listing(
        expected.community.identifier,
        expected.package.namespace.name,
        expected.package.name,
    )

    assert actual.community.identifier == expected.community.identifier
    assert actual.package.namespace.name == expected.package.namespace.name
    assert actual.package.name == expected.package.name


@pytest.mark.django_db
def test_get_custom_package_listing__treats_package_name_as_case_insensitive() -> None:
    expected = PackageListingFactory()

    requested_as_uppercase = get_custom_package_listing(
        expected.community.identifier,
        expected.package.namespace.name,
        expected.package.name.upper(),
    )
    requested_as_lowercase = get_custom_package_listing(
        expected.community.identifier,
        expected.package.namespace.name,
        expected.package.name.lower(),
    )

    assert requested_as_uppercase.package.name == expected.package.name
    assert requested_as_lowercase.package.name == expected.package.name


@pytest.mark.django_db
def test_get_custom_package_listing__annotates_downloads_and_ratings() -> None:
    listing = PackageListingFactory(package_version_kwargs={"downloads": 100})
    PackageVersionFactory(
        package=listing.package,
        version_number="1.0.1",
        downloads=20,
    )
    PackageVersionFactory(
        package=listing.package,
        version_number="1.0.2",
        downloads=3,
    )

    [PackageRatingFactory(package=listing.package) for _ in range(3)]

    actual = get_custom_package_listing(
        listing.community.identifier,
        listing.package.namespace.name,
        listing.package.name.upper(),
    )

    assert actual.download_count == 123
    assert actual.rating_count == 3


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("changelog", "expected"),
    (
        (None, False),
        ("", True),
        (" ", True),  # Space
        ("  ", True),  # Tab
        ("# Oh hai", True),
    ),
)
def test_get_custom_package_listing__annotates_has_changelog(
    changelog: Optional[str],
    expected: bool,
) -> None:
    listing = PackageListingFactory(package_version_kwargs={"changelog": changelog})

    actual = get_custom_package_listing(
        listing.community.identifier,
        listing.package.namespace.name,
        listing.package.name.upper(),
    )

    assert actual.has_changelog == expected


@pytest.mark.django_db
def test_get_custom_package_listing__augments_listing_with_dependant_count() -> None:
    listing = PackageListingFactory()
    dependant_count = 5

    for _ in range(dependant_count):
        dependant = PackageVersionFactory()
        dependant.dependencies.add(listing.package.latest)

    actual = get_custom_package_listing(
        listing.community.identifier,
        listing.package.namespace.name,
        listing.package.name.upper(),
    )

    assert actual.dependant_count == dependant_count


@pytest.mark.django_db
def test_get_custom_package_listing__augments_listing_with_dependency_count() -> None:
    listing = PackageListingFactory()
    dependency_count = 5
    dependencies = PackageListingFactory.create_batch(
        dependency_count,
        community=listing.community,
    )
    listing.package.latest.dependencies.set(d.package.latest for d in dependencies)

    actual = get_custom_package_listing(
        listing.community.identifier,
        listing.package.namespace.name,
        listing.package.name.upper(),
    )

    assert actual.dependency_count == dependency_count


@pytest.mark.django_db
def test_get_custom_package_listing__augments_listing_with_dependencies_from_same_community() -> None:
    dependant = PackageListingFactory()
    dependency1 = PackageListingFactory(community=dependant.community)
    dependency2 = PackageListingFactory()
    dependency3 = PackageListingFactory(community=dependant.community)
    dependant.package.latest.dependencies.set(
        [
            dependency1.package.latest,
            dependency2.package.latest,
            dependency3.package.latest,
        ],
    )

    actual = get_custom_package_listing(
        dependant.community.identifier,
        dependant.package.namespace.name,
        dependant.package.name.upper(),
    )

    assert actual.dependencies.count() == 2
    assert dependency1.package.latest in actual.dependencies
    assert dependency2.package.latest not in actual.dependencies
    assert dependency3.package.latest in actual.dependencies


@pytest.mark.django_db
def test_get_custom_package_listing__when_many_dependencies__returns_only_four() -> None:
    listing = PackageListingFactory()
    dependency_count = 6
    dependencies = PackageListingFactory.create_batch(
        dependency_count,
        community=listing.community,
    )
    listing.package.latest.dependencies.set(d.package.latest for d in dependencies)

    actual = get_custom_package_listing(
        listing.community.identifier,
        listing.package.namespace.name,
        listing.package.name.upper(),
    )

    assert actual.dependencies.count() == 4


@pytest.mark.django_db
def test_package_listing_view__returns_info(api_client: APIClient) -> None:
    community = CommunityFactory()
    category = PackageCategoryFactory(community=community)
    listing = PackageListingFactory(
        community=community,
        categories=[category],
        package_kwargs={"is_pinned": True},
        package_version_kwargs={
            "changelog": " ",
            "downloads": 99,
            "website_url": "https://thunderstore.io/",
        },
    )
    latest = listing.package.latest
    dependant = PackageVersionFactory()
    dependant.dependencies.set([latest])
    dependency = PackageListingFactory(community=community)
    latest.dependencies.set([dependency.package.latest])
    [PackageRatingFactory(package=listing.package) for _ in range(8)]
    owner = TeamMemberFactory(team=listing.package.owner, role="owner")
    member = TeamMemberFactory(team=listing.package.owner, role="member")

    response = api_client.get(
        f"/api/cyberstorm/listing/{community.identifier}/{listing.package.namespace}/{listing.package.name}/",
    )
    actual = response.json()

    assert len(actual["categories"]) == 1
    assert actual["categories"][0]["id"] == str(category.id)
    assert actual["community_identifier"] == community.identifier
    assert actual["community_name"] == community.name
    assert actual["datetime_created"] == _date_to_z(latest.date_created)
    assert actual["dependant_count"] == 1
    assert len(actual["dependencies"]) == 1
    assert actual["dependencies"][0]["community_identifier"] == community.identifier
    assert actual["dependencies"][0]["namespace"] == dependency.package.namespace.name
    assert actual["dependencies"][0]["name"] == dependency.package.name
    assert actual["description"] == latest.description
    assert actual["download_count"] == 99
    assert actual["download_url"] == latest.full_download_url
    assert actual["full_version_name"] == latest.full_version_name
    assert actual["has_changelog"] == (latest.changelog is not None)
    assert actual["icon_url"] == latest.icon.url
    assert actual["install_url"] == latest.install_url
    assert actual["is_deprecated"] == listing.package.is_deprecated
    assert actual["is_nsfw"] == listing.has_nsfw_content
    assert actual["is_pinned"] == listing.package.is_pinned
    assert actual["last_updated"] == _date_to_z(listing.package.date_updated)
    assert actual["latest_version_number"] == latest.version_number
    assert actual["name"] == listing.package.name
    assert actual["namespace"] == listing.package.namespace.name
    assert actual["rating_count"] == 8
    assert actual["size"] == latest.file_size
    assert actual["team"]["name"] == listing.package.owner.name
    assert len(actual["team"]["members"]) == 2
    assert actual["team"]["members"][0]["identifier"] == owner.user.id
    assert actual["team"]["members"][0]["role"] == "owner"
    assert actual["team"]["members"][1]["identifier"] == member.user.id
    assert actual["team"]["members"][1]["role"] == "member"
    assert actual["website_url"] == latest.website_url


@pytest.mark.django_db
def test_package_listing_view__serializes_url_correctly(api_client: APIClient) -> None:
    l = PackageListingFactory(
        package_version_kwargs={
            "website_url": "https://thunderstore.io/",
        },
    )

    url = f"/api/cyberstorm/listing/{l.community.identifier}/{l.package.namespace}/{l.package.name}/"
    response = api_client.get(url)
    actual = response.json()

    assert actual["website_url"] == "https://thunderstore.io/"

    l.package.latest.website_url = ""
    l.package.latest.save(update_fields=("website_url",))

    response = api_client.get(url)
    actual = response.json()

    assert actual["website_url"] is None


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("package_is_active", "version_is_active"),
    (
        (False, False),
        (True, False),
        (False, True),
        (True, True),
    ),
)
def test_dependency_serializer__reads_is_active_from_correct_field(
    package_is_active: bool,
    version_is_active: bool,
) -> None:
    dependant = PackageVersionFactory()
    dependency = PackageVersionFactory(is_active=version_is_active)
    dependency.package.is_active = package_is_active
    dependency.package.save()
    dependant.dependencies.set([dependency])

    # community_identifier is normally added using annotations, but
    # it's irrelavant for this test case.
    dependency.community_identifier = "greendale"

    actual = DependencySerializer(dependency).data

    assert actual["is_active"] == (package_is_active and version_is_active)


@pytest.mark.django_db
def test_dependency_serializer__when_dependency_is_not_active__censors_icon_and_description() -> None:
    # community_identifier is normally added using annotations, but
    # it's irrelavant for this test case.
    dependency = PackageVersionFactory()
    dependency.community_identifier = "greendale"

    actual = DependencySerializer(dependency).data

    assert actual["description"].startswith("Desc_")
    assert actual["icon_url"].startswith("http")

    dependency.is_active = False
    del dependency.is_effectively_active  # Clear cached property
    actual = DependencySerializer(dependency).data

    assert actual["description"] == "This package has been removed."
    assert actual["icon_url"] is None


@pytest.mark.django_db
def test_package_listing_edit_categories_view__returns_error_for_non_existent_package_listing(
    api_client: APIClient,
    team_member: TeamMember,
    active_package_listing: PackageListing,
    package_categories: List[PackageCategory],
) -> None:
    active_package_listing.categories.set(package_categories)
    active_package_listing.save()
    apl_categories = active_package_listing.categories.all()
    assert len(apl_categories) == 3

    api_client.force_authenticate(team_member.user)
    response = api_client.post(
        f"/api/cyberstorm/listing/BAD/{active_package_listing.package.namespace.name}/{active_package_listing.package.name}/edit/categories/",
        json.dumps(
            {
                "current_categories": [x.slug for x in apl_categories],
                "new_categories": [
                    x.slug for x in [apl_categories[0], apl_categories[1]]
                ],
            }
        ),
        content_type="application/json",
    )
    actual = response.json()

    assert actual["detail"] == "Not found."
    assert (
        len(
            set(apl_categories).symmetric_difference(
                PackageListing.objects.get(
                    pk=active_package_listing.pk
                ).categories.all()
            )
        )
        == 0
    )

    response = api_client.post(
        f"/api/cyberstorm/listing/{active_package_listing.community.identifier}/BAD/{active_package_listing.package.name}/edit/categories/",
        json.dumps(
            {
                "current_categories": [x.slug for x in apl_categories],
                "new_categories": [
                    x.slug for x in [apl_categories[0], apl_categories[1]]
                ],
            }
        ),
        content_type="application/json",
    )
    actual = response.json()

    assert actual["detail"] == "Not found."
    assert (
        len(
            set(apl_categories).symmetric_difference(
                PackageListing.objects.get(
                    pk=active_package_listing.pk
                ).categories.all()
            )
        )
        == 0
    )

    response = api_client.post(
        f"/api/cyberstorm/listing/{active_package_listing.community.identifier}/{active_package_listing.package.namespace.name}/BAD/edit/categories/",
        json.dumps(
            {
                "current_categories": [x.slug for x in apl_categories],
                "new_categories": [
                    x.slug for x in [apl_categories[0], apl_categories[1]]
                ],
            }
        ),
        content_type="application/json",
    )
    actual = response.json()

    assert actual["detail"] == "Not found."
    assert (
        len(
            set(apl_categories).symmetric_difference(
                PackageListing.objects.get(
                    pk=active_package_listing.pk
                ).categories.all()
            )
        )
        == 0
    )


@pytest.mark.django_db
def test_package_listing_edit_categories_view__correct_values__remove_one_category__succeeds(
    api_client: APIClient,
    team_member: TeamMember,
    active_package_listing: PackageListing,
    package_categories: List[PackageCategory],
) -> None:
    active_package_listing.categories.set(package_categories)
    active_package_listing.save()
    apl_categories = active_package_listing.categories.all()
    assert len(apl_categories) == 3

    api_client.force_authenticate(team_member.user)
    response = api_client.post(
        f"/api/cyberstorm/listing/{active_package_listing.community.identifier}/{active_package_listing.package.namespace.name}/{active_package_listing.package.name}/edit/categories/",
        json.dumps(
            {
                "current_categories": [x.slug for x in apl_categories],
                "new_categories": [
                    x.slug for x in [apl_categories[0], apl_categories[1]]
                ],
            }
        ),
        content_type="application/json",
    )
    actual = response.json()

    assert actual["categories"] == [
        {"id": str(x.id), "name": x.name, "slug": x.slug}
        for x in [apl_categories[0], apl_categories[1]]
    ]


@pytest.mark.django_db
def test_package_listing_edit_categories_view__correct_values__no_user__fails(
    api_client: APIClient,
    active_package_listing: PackageListing,
    package_categories: List[PackageCategory],
) -> None:
    active_package_listing.categories.set(package_categories)
    active_package_listing.save()
    apl_categories = active_package_listing.categories.all()
    assert len(apl_categories) == 3

    response = api_client.post(
        f"/api/cyberstorm/listing/{active_package_listing.community.identifier}/{active_package_listing.package.namespace.name}/{active_package_listing.package.name}/edit/categories/",
        json.dumps(
            {
                "current_categories": [x.slug for x in apl_categories],
                "new_categories": [
                    x.slug for x in [apl_categories[0], apl_categories[1]]
                ],
            }
        ),
        content_type="application/json",
    )
    actual = response.json()

    assert actual["detail"] == "Authentication credentials were not provided."


@pytest.mark.django_db
def test_package_listing_edit_categories_view__wrong_current_categories__fails(
    api_client: APIClient,
    team_member: TeamMember,
    active_package_listing: PackageListing,
    package_categories: List[PackageCategory],
) -> None:
    active_package_listing.categories.set(package_categories)
    active_package_listing.save()
    apl_categories = active_package_listing.categories.all()
    assert len(apl_categories) == 3

    api_client.force_authenticate(team_member.user)
    response = api_client.post(
        f"/api/cyberstorm/listing/{active_package_listing.community.identifier}/{active_package_listing.package.namespace.name}/{active_package_listing.package.name}/edit/categories/",
        json.dumps(
            {"current_categories": [apl_categories[0].slug], "new_categories": []}
        ),
        content_type="application/json",
    )
    actual = response.json()

    assert actual["__all__"] == [
        "Listings current categories do not match provided ones"
    ]
    assert (
        len(
            set(apl_categories).symmetric_difference(
                PackageListing.objects.get(
                    pk=active_package_listing.pk
                ).categories.all()
            )
        )
        == 0
    )


@pytest.mark.django_db
def test_package_listing_edit_categories_view__correct_values__remove_all_categories__succeeds(
    api_client: APIClient,
    team_member: TeamMember,
    active_package_listing: PackageListing,
    package_categories: List[PackageCategory],
) -> None:
    active_package_listing.categories.set(package_categories)
    active_package_listing.save()
    apl_categories = active_package_listing.categories.all()
    assert len(apl_categories) == 3

    api_client.force_authenticate(team_member.user)
    response = api_client.post(
        f"/api/cyberstorm/listing/{active_package_listing.community.identifier}/{active_package_listing.package.namespace.name}/{active_package_listing.package.name}/edit/categories/",
        json.dumps(
            {
                "current_categories": [x.slug for x in apl_categories],
                "new_categories": [],
            }
        ),
        content_type="application/json",
    )
    actual = response.json()

    assert len(actual["categories"]) == 0


@pytest.mark.django_db
def test_package_listing_edit_categories_view__bad_values__fails(
    api_client: APIClient,
    team_member: TeamMember,
    active_package_listing: PackageListing,
    package_categories: List[PackageCategory],
) -> None:
    active_package_listing.categories.set(package_categories)
    active_package_listing.save()
    apl_categories = active_package_listing.categories.all()
    assert len(apl_categories) == 3

    api_client.force_authenticate(team_member.user)
    response = api_client.post(
        f"/api/cyberstorm/listing/{active_package_listing.community.identifier}/{active_package_listing.package.namespace.name}/{active_package_listing.package.name}/edit/categories/",
        json.dumps(
            {
                "current_categories": [x.slug for x in apl_categories],
                "new_categories": "bad",
            }
        ),
        content_type="application/json",
    )
    actual = response.json()

    assert 'Expected a list of items but got type "str".' in str(
        actual["new_categories"]
    )

    response = api_client.post(
        f"/api/cyberstorm/listing/{active_package_listing.community.identifier}/{active_package_listing.package.namespace.name}/{active_package_listing.package.name}/edit/categories/",
        json.dumps(
            {
                "current_categories": "bad",
                "new_categories": [
                    x.slug for x in [apl_categories[0], apl_categories[1]]
                ],
            }
        ),
        content_type="application/json",
    )
    actual = response.json()

    assert 'Expected a list of items but got type "str".' in str(
        actual["current_categories"]
    )


def _date_to_z(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
