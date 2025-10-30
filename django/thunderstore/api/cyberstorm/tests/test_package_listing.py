from datetime import datetime
from typing import Optional
from unittest.mock import Mock, PropertyMock, patch

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from conftest import TestUserTypes
from thunderstore.api.cyberstorm.views.package_listing import (
    DependencySerializer,
    get_custom_package_listing,
)
from thunderstore.community.factories import (
    Community,
    CommunityFactory,
    PackageCategoryFactory,
    PackageListingFactory,
)
from thunderstore.repository.factories import (
    NamespaceFactory,
    PackageRatingFactory,
    PackageVersionFactory,
    TeamMemberFactory,
)


def get_listing_url(package_listing) -> str:
    base_url = "/api/cyberstorm/listing"

    community_id = package_listing.community.identifier
    namespace_id = package_listing.package.namespace.name
    package_name = package_listing.package.name

    return f"{base_url}/{community_id}/{namespace_id}/{package_name}/status/"


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
        listing.package.name,
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
        listing.package.name,
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
        listing.package.name,
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
        listing.package.name,
    )

    assert actual.dependency_count == dependency_count


@pytest.mark.django_db
def test_get_custom_package_listing__augments_listing_with_dependencies_from_same_community() -> (
    None
):
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
        dependant.package.name,
    )

    assert actual.dependencies.count() == 2
    assert dependency1.package.latest in actual.dependencies
    assert dependency2.package.latest not in actual.dependencies
    assert dependency3.package.latest in actual.dependencies


@pytest.mark.django_db
def test_get_custom_package_listing__when_many_dependencies__returns_only_four() -> (
    None
):
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
        listing.package.name,
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
    assert len(actual["team"]["members"]) == 0
    assert actual["website_url"] == latest.website_url
    assert actual["version_count"] == 1


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

    dependency.community_identifier = "greendale"
    dependency.version_is_unavailable = False

    actual = DependencySerializer(dependency).data

    assert actual["is_active"] == (package_is_active and version_is_active)


@pytest.mark.django_db
def test_dependency_serializer__when_dependency_is_not_active__censors_icon_and_description() -> (
    None
):
    dependency = PackageVersionFactory()
    dependency.community_identifier = "greendale"
    dependency.version_is_unavailable = False

    actual = DependencySerializer(dependency).data

    assert actual["description"].startswith("Desc_")
    assert actual["icon_url"].startswith("http")

    dependency.is_active = False
    del dependency.is_effectively_active  # Clear cached property
    actual = DependencySerializer(dependency).data

    assert actual["description"] == "This package has been removed."
    assert actual["icon_url"] is None


def _date_to_z(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


@pytest.mark.django_db
@pytest.mark.parametrize("return_val", [True, False])
def test_package_listing_is_removed(
    return_val: bool,
    api_client: APIClient,
    community: Community,
) -> None:
    package = "Mod"
    target_ns = NamespaceFactory()

    target_dependency = PackageListingFactory(
        community_=community,
        package_kwargs={"name": package, "namespace": target_ns},
    )

    target_package = PackageListingFactory(community_=community)
    target_package.package.latest.dependencies.set(
        [target_dependency.package.latest.id],
    )

    community_id = target_package.community.identifier
    namespace = target_package.package.namespace.name
    package_name = target_package.package.name

    url = f"/api/cyberstorm/listing/{community_id}/{namespace}/{package_name}/"

    path = "thunderstore.repository.models.package_version.PackageVersion.is_removed"
    with patch(path, new_callable=PropertyMock) as is_removed_property:
        is_removed_property.return_value = return_val
        response = api_client.get(url)
        response_dependencies = response.json()["dependencies"][0]

    assert "is_removed" in response_dependencies
    assert response_dependencies["is_removed"] == return_val


@pytest.mark.django_db
@pytest.mark.parametrize("return_val", [True, False])
@patch("thunderstore.repository.models.package_version.PackageVersion.is_unavailable")
def test_package_listing_is_unavailable(
    is_unavailable_func: Mock,
    return_val: bool,
    api_client: APIClient,
    community: Community,
) -> None:
    is_unavailable_func.return_value = return_val

    package = "Mod"
    target_ns = NamespaceFactory()

    target_dependency = PackageListingFactory(
        community_=community,
        package_kwargs={"name": package, "namespace": target_ns},
    )

    target_package = PackageListingFactory(community_=community)
    target_package.package.latest.dependencies.set(
        [target_dependency.package.latest.id],
    )

    community_id = target_package.community.identifier
    namespace = target_package.package.namespace.name
    package_name = target_package.package.name

    url = f"/api/cyberstorm/listing/{community_id}/{namespace}/{package_name}/"
    response = api_client.get(url)
    response_dependencies = response.json()["dependencies"][0]

    assert "is_unavailable" in response_dependencies
    assert response_dependencies["is_unavailable"] == return_val


@pytest.mark.django_db
def test_package_listing_query_count(
    api_client: APIClient, community: Community
) -> None:
    package = "Mod"
    target_ns = NamespaceFactory()

    target_dependencies = [
        PackageListingFactory(
            community_=community,
            package_kwargs={"name": f"{package}_{i}", "namespace": target_ns},
        )
        for i in range(10)
    ]

    target_package = PackageListingFactory(community_=community)
    target_package.package.latest.dependencies.set(
        [dep.package.latest.id for dep in target_dependencies],
    )

    community_id = target_package.community.identifier
    namespace = target_package.package.namespace.name
    package_name = target_package.package.name

    url = f"/api/cyberstorm/listing/{community_id}/{namespace}/{package_name}/"

    with CaptureQueriesContext(connection) as ctx:
        response = api_client.get(url)

    assert response.status_code == 200
    assert len(ctx.captured_queries) < 23


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
def test_get_package_listing_status(
    active_package_listing, api_client, user_type
) -> None:
    base_url = "/api/cyberstorm/listing"
    community_id = active_package_listing.community.identifier
    namespace_id = active_package_listing.package.namespace.name
    package_name = active_package_listing.package.name
    url = f"{base_url}/{community_id}/{namespace_id}/{package_name}/status/"

    user = TestUserTypes.get_user_by_type(user_type)

    is_fake_user = user_type in TestUserTypes.fake_users()
    is_unauthenticated = user_type == TestUserTypes.unauthenticated

    if not is_fake_user and not is_unauthenticated:
        api_client.force_authenticate(user=user)

    response = api_client.get(url)

    expected_status_code = {
        TestUserTypes.no_user: 401,
        TestUserTypes.unauthenticated: 401,
        TestUserTypes.regular_user: 403,
        TestUserTypes.deactivated_user: 403,
        TestUserTypes.service_account: 403,
        TestUserTypes.site_admin: 200,
        TestUserTypes.superuser: 200,
    }

    assert response.status_code == expected_status_code[user_type]


@pytest.mark.django_db
@pytest.mark.parametrize("return_val", [True, False])
@patch(
    "thunderstore.repository.views.package.detail.PermissionsChecker.can_manage",
    new_callable=PropertyMock,
)
def test_package_listing_status_can_manage_permission(
    mock_can_manage, return_val, api_client, active_package_listing
):
    active_package_listing.rejection_reason = "Inappropriate content"
    active_package_listing.review_status = "rejected"
    active_package_listing.save()

    mock_can_manage.return_value = return_val

    user = TestUserTypes.get_user_by_type(TestUserTypes.superuser)
    api_client.force_authenticate(user=user)

    url = get_listing_url(active_package_listing)
    response = api_client.get(url)

    data = response.json()

    if return_val:
        assert data["review_status"] == "rejected"
        assert data["rejection_reason"] == "Inappropriate content"
    else:
        assert data["review_status"] is None
        assert data["rejection_reason"] is None


@pytest.mark.django_db
@pytest.mark.parametrize("return_val", [True, False])
@patch(
    "thunderstore.repository.views.package.detail.PermissionsChecker.can_view_listing_admin_page",
    new_callable=PropertyMock,
)
def test_package_listing_status_can_view_listing_admin_page_permission(
    mock_can_view_listing_admin_page, return_val, api_client, active_package_listing
):
    mock_can_view_listing_admin_page.return_value = return_val

    user = TestUserTypes.get_user_by_type(TestUserTypes.superuser)
    api_client.force_authenticate(user=user)

    url = get_listing_url(active_package_listing)
    response = api_client.get(url)

    data = response.json()

    if return_val:
        assert data["listing_admin_url"] == active_package_listing.get_admin_url()
    else:
        assert data["listing_admin_url"] is None


@pytest.mark.django_db
@pytest.mark.parametrize("return_val", [True, False])
@patch(
    "thunderstore.repository.views.package.detail.PermissionsChecker.can_moderate",
    new_callable=PropertyMock,
)
def test_package_listing_status_can_moderate_permission(
    mock_can_moderate, return_val, api_client, active_package_listing
):
    mock_can_moderate.return_value = return_val

    active_package_listing.notes = "This package contains inappropriate content."
    active_package_listing.save()

    user = TestUserTypes.get_user_by_type(TestUserTypes.superuser)
    api_client.force_authenticate(user=user)

    url = get_listing_url(active_package_listing)
    response = api_client.get(url)

    data = response.json()

    if return_val:
        assert data["internal_notes"] == "This package contains inappropriate content."
    else:
        assert data["internal_notes"] is None
