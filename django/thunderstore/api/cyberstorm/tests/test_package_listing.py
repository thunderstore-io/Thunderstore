from datetime import datetime
from typing import Optional
from unittest.mock import PropertyMock, patch

import pytest
from cachalot.api import cachalot_disabled
from django.db import connection
from django.http import Http404
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from conftest import TestUserTypes
from thunderstore.api.cyberstorm.views.package_listing import (
    DependencySerializer,
    get_custom_package_listing,
)
from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.factories import (
    Community,
    CommunityFactory,
    PackageCategoryFactory,
    PackageListingFactory,
)
from thunderstore.community.models import PackageListing
from thunderstore.repository.factories import (
    PackageRatingFactory,
    PackageVersionFactory,
    TeamMemberFactory,
)
from thunderstore.repository.models import PackageVersion


def get_listing_url(package_listing) -> str:
    base_url = "/api/cyberstorm/listing"

    community_id = package_listing.community.identifier
    namespace_id = package_listing.package.namespace.name
    package_name = package_listing.package.name

    return f"{base_url}/{community_id}/{namespace_id}/{package_name}/status/"


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
def test_get_custom_package_listing__rejected_package_visibility_user_types(
    user_type,
) -> None:
    listing = PackageListingFactory(review_status="rejected")

    community_id = listing.community.identifier
    namespace = listing.package.namespace.name
    package_name = listing.package.name
    user = TestUserTypes.get_user_by_type(user_type)

    expected_visibility = {
        TestUserTypes.no_user: False,
        TestUserTypes.unauthenticated: False,
        TestUserTypes.regular_user: False,
        TestUserTypes.deactivated_user: False,
        TestUserTypes.service_account: False,
        TestUserTypes.site_admin: True,
        TestUserTypes.superuser: True,
    }

    is_visible = expected_visibility[user_type]

    if is_visible:
        listing = get_custom_package_listing(
            community_id,
            namespace,
            package_name,
            user=user,
        )
    else:
        with pytest.raises(Http404):
            listing = get_custom_package_listing(
                community_id,
                namespace,
                package_name,
                user=user,
            )


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
def test_get_custom_package_listing__when_version_provided__uses_that_version() -> None:
    listing = PackageListingFactory(
        package_version_kwargs={
            "version_number": "1.0.0",
            "description": "Initial upload",
            "changelog": None,
        }
    )
    expected = PackageVersionFactory(
        package=listing.package,
        version_number="1.2.0",
        description="We want this package version",
        changelog="We want this changelog",
    )
    PackageVersionFactory(
        package=listing.package,
        version_number="1.2.3",
        description="Latest upload",
        changelog=None,
    )

    actual = get_custom_package_listing(
        listing.community.identifier,
        listing.package.namespace.name,
        listing.package.name,
        version="1.2.0",
    )

    assert actual.version.id == expected.id
    assert actual.version.version_number == "1.2.0"
    assert actual.has_changelog is True


@pytest.mark.django_db
def test_get_custom_package_listing__when_version_provided_but_missing__raises_404() -> None:
    listing = PackageListingFactory()

    with pytest.raises(Http404):
        get_custom_package_listing(
            listing.community.identifier,
            listing.package.namespace.name,
            listing.package.name,
            version="6.6.6",
        )


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
    assert actual["latest_version_number"] == latest.version_number
    assert actual["name"] == listing.package.name
    assert actual["namespace"] == listing.package.namespace.name
    assert actual["package_created"] == _date_to_z(listing.package.date_created)
    assert actual["rating_count"] == 8
    assert actual["size"] == latest.file_size
    assert actual["team"]["name"] == listing.package.owner.name
    assert len(actual["team"]["members"]) == 0
    assert actual["website_url"] == latest.website_url
    assert actual["version_count"] == 1
    assert actual["version_created"] == _date_to_z(latest.date_created)


@pytest.mark.django_db
def test_package_listing_view__when_version_provided__uses_that_version(
    api_client: APIClient,
) -> None:
    community = CommunityFactory()
    listing = PackageListingFactory(
        community=community,
        package_version_kwargs={
            "version_number": "1.0.0",
            "description": "Initial upload",
            "changelog": None,
        },
    )
    expected = PackageVersionFactory(
        package=listing.package,
        version_number="1.0.1",
        description="Expected version",
        changelog="Expected changelog",
    )
    latest = PackageVersionFactory(
        package=listing.package,
        version_number="1.0.2",
        description="Latest upload",
        changelog=None,
    )

    url = (
        f"/api/cyberstorm/listing/{community.identifier}/{listing.package.namespace}/{listing.package.name}/"
        f"v/{expected.version_number}/"
    )
    response = api_client.get(url)
    actual = response.json()

    assert response.status_code == 200
    assert actual["description"] == expected.description
    assert actual["latest_version_number"] == latest.version_number
    assert actual["has_changelog"] is True


@pytest.mark.django_db
def test_package_listing_view__when_incorrect_version_provided__returns_404(
    api_client: APIClient,
) -> None:
    community = CommunityFactory()
    listing = PackageListingFactory(
        community=community,
        package_version_kwargs={
            "version_number": "1.0.0",
            "description": "Initial upload",
            "changelog": None,
        },
    )

    url = (
        f"/api/cyberstorm/listing/{community.identifier}/{listing.package.namespace}/{listing.package.name}/"
        f"v/0.0.0/"
    )
    response = api_client.get(url)

    assert response.status_code == 404


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
    dependency.package_has_active_versions = version_is_active
    dependency.listing_is_available = True

    actual = DependencySerializer(dependency).data

    assert actual["is_active"] == (package_is_active and version_is_active)


@pytest.mark.django_db
def test_dependency_serializer__when_dependency_is_not_active__censors_icon_and_description() -> (
    None
):
    dependency = PackageVersionFactory()
    dependency.community_identifier = "greendale"
    dependency.package_has_active_versions = True
    dependency.listing_is_available = True

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


def _get_listing_detail_url(listing: PackageListing, use_version_route: bool) -> str:
    url = (
        f"/api/cyberstorm/listing/{listing.community.identifier}/"
        f"{listing.package.namespace.name}/{listing.package.name}/"
    )
    if use_version_route:
        url += f"v/{listing.package.latest.version_number}/"
    return url


def _create_dependency(
    community: Community,
    version_is_active: bool = True,
    has_other_active_version: bool = False,
    package_is_active: bool = True,
    review_status: str = PackageListingReviewStatus.approved,
) -> PackageVersion:
    version = PackageVersionFactory(is_active=version_is_active)
    if has_other_active_version:
        PackageVersionFactory(package=version.package, version_number="2.0.0")
    version.package.is_active = package_is_active
    version.package.save(update_fields=("is_active",))
    PackageListingFactory(
        community=community,
        package_=version.package,
        review_status=review_status,
    )
    return version


@pytest.mark.django_db
@pytest.mark.parametrize("use_version_route", (False, True))
@pytest.mark.parametrize(
    (
        "dependency_kwargs",
        "require_approval",
        "expected_is_removed",
        "expected_is_unavailable",
    ),
    (
        pytest.param({}, False, False, False, id="available"),
        pytest.param(
            {"version_is_active": False, "has_other_active_version": True},
            False,
            True,
            True,
            id="version_inactive",
        ),
        pytest.param(
            {"package_is_active": False},
            False,
            True,
            True,
            id="package_inactive",
        ),
        pytest.param(
            {"version_is_active": False},
            False,
            True,
            True,
            id="no_active_versions",
        ),
        pytest.param(
            {"review_status": PackageListingReviewStatus.rejected},
            False,
            False,
            True,
            id="listing_rejected",
        ),
        pytest.param(
            {"review_status": PackageListingReviewStatus.unreviewed},
            True,
            False,
            True,
            id="listing_unreviewed_approval_required",
        ),
        pytest.param(
            {"review_status": PackageListingReviewStatus.unreviewed},
            False,
            False,
            False,
            id="listing_unreviewed_approval_not_required",
        ),
    ),
)
def test_package_listing_view__dependency_availability(
    api_client: APIClient,
    use_version_route: bool,
    dependency_kwargs: dict,
    require_approval: bool,
    expected_is_removed: bool,
    expected_is_unavailable: bool,
) -> None:
    community = CommunityFactory(require_package_listing_approval=require_approval)
    dependency = _create_dependency(community, **dependency_kwargs)
    listing = PackageListingFactory(
        community=community,
        review_status=PackageListingReviewStatus.approved,
    )
    listing.package.latest.dependencies.set([dependency])

    response = api_client.get(_get_listing_detail_url(listing, use_version_route))

    assert response.status_code == 200
    [actual] = response.json()["dependencies"]
    assert actual["is_removed"] == expected_is_removed
    assert actual["is_unavailable"] == expected_is_unavailable


@pytest.mark.django_db
@pytest.mark.parametrize("use_version_route", (False, True))
def test_package_listing_view__query_count_does_not_depend_on_dependencies(
    api_client: APIClient,
    use_version_route: bool,
) -> None:
    community = CommunityFactory()

    def get_query_count(dependency_count: int) -> int:
        listing = PackageListingFactory(community=community)
        listing.package.latest.dependencies.set(
            _create_dependency(community) for _ in range(dependency_count)
        )
        url = _get_listing_detail_url(listing, use_version_route)

        # cachalot would serve repeated identical queries from Redis, which
        # hides them from the count.
        with cachalot_disabled(), CaptureQueriesContext(connection) as ctx:
            response = api_client.get(url)

        assert response.status_code == 200
        assert len(response.json()["dependencies"]) == dependency_count
        return len(ctx.captured_queries)

    # The first request also caches the request's Site (get_current_site() in
    # CommunitySiteMiddleware), which costs one extra query.
    get_query_count(0)

    assert get_query_count(0) == get_query_count(4)


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
    "thunderstore.repository.views.package.detail.PermissionsChecker.can_view_package_admin_page",
    new_callable=PropertyMock,
)
def test_package_listing_status_can_view_package_admin_page_permission(
    mock_can_view_package_admin_page, return_val, api_client, active_package_listing
):
    mock_can_view_package_admin_page.return_value = return_val

    user = TestUserTypes.get_user_by_type(TestUserTypes.superuser)
    api_client.force_authenticate(user=user)

    url = get_listing_url(active_package_listing)
    response = api_client.get(url)

    data = response.json()

    if return_val:
        assert (
            data["package_admin_url"] == active_package_listing.package.get_admin_url()
        )
    else:
        assert data["package_admin_url"] is None


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
