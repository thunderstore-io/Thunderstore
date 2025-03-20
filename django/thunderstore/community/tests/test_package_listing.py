import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from conftest import TestUserTypes
from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.factories import (
    CommunityFactory,
    CommunitySiteFactory,
    PackageCategoryFactory,
    PackageListingFactory,
    PackageVersionFactory,
)
from thunderstore.community.models import (
    Community,
    CommunityAggregatedFields,
    CommunityMemberRole,
    CommunityMembership,
    PackageCategory,
    PackageListing,
)
from thunderstore.community.tasks import detect_and_assign_modpack_category
from thunderstore.repository.models import Package, TeamMember, TeamMemberRole


@pytest.mark.django_db
@pytest.mark.parametrize("with_site", (False, True))
def test_package_listing_get_absolute_url(
    active_package_listing: PackageListing,
    with_site: bool,
) -> None:
    if with_site:
        CommunitySiteFactory(community=active_package_listing.community)
        expected = "/".join(
            [
                "/package",
                active_package_listing.package.owner.name,
                active_package_listing.package.name,
                "",
            ],
        )
    else:
        expected = "/".join(
            [
                "/c",
                active_package_listing.community.identifier,
                "p",
                active_package_listing.package.owner.name,
                active_package_listing.package.name,
                "",
            ],
        )

    assert active_package_listing.get_absolute_url() == expected


@pytest.mark.django_db
@pytest.mark.parametrize("with_site", (False, True))
def test_package_listing_owner_url(
    active_package_listing: PackageListing,
    with_site: bool,
) -> None:
    if with_site:
        CommunitySiteFactory(community=active_package_listing.community)
        expected = "/".join(
            [
                "/package",
                active_package_listing.package.owner.name,
                "",
            ],
        )
    else:
        expected = "/".join(
            [
                "/c",
                active_package_listing.community.identifier,
                "p",
                active_package_listing.package.owner.name,
                "",
            ],
        )
    assert active_package_listing.owner_url == expected


@pytest.mark.django_db
@pytest.mark.parametrize("with_site", (False, True))
def test_package_listing_dependants_url(
    active_package_listing: PackageListing,
    with_site: bool,
) -> None:
    if with_site:
        CommunitySiteFactory(community=active_package_listing.community)
        expected = "/".join(
            [
                "/package",
                active_package_listing.package.owner.name,
                active_package_listing.package.name,
                "dependants/",
            ],
        )
    else:
        expected = "/".join(
            [
                "/c",
                active_package_listing.community.identifier,
                "p",
                active_package_listing.package.owner.name,
                active_package_listing.package.name,
                "dependants/",
            ],
        )

    assert active_package_listing.dependants_url == expected


@pytest.mark.django_db
def test_package_listing_only_one_per_community(
    active_package: Package,
    community: Community,
) -> None:
    l1 = PackageListing.objects.create(package=active_package, community=community)
    assert l1.pk
    with pytest.raises(IntegrityError) as exc:
        PackageListing.objects.create(package=active_package, community=community)
    assert "one_listing_per_community" in str(exc.value)


@pytest.mark.django_db
def test_package_listing_community_read_only(
    active_package_listing: PackageListing,
) -> None:
    c = Community.objects.create(name="Test Community")
    active_package_listing.community = c
    with pytest.raises(ValidationError) as exc:
        active_package_listing.save()
    assert "PackageListing.community is read only" in str(exc.value)


@pytest.mark.django_db
@pytest.mark.parametrize("require_approval", (False, True))
@pytest.mark.parametrize("review_status", PackageListingReviewStatus.options())
def test_package_listing_is_waiting_for_approval(
    active_package_listing: PackageListing,
    require_approval: bool,
    review_status: str,
) -> None:
    active_package_listing.review_status = review_status
    active_package_listing.save()
    community = active_package_listing.community
    community.require_package_listing_approval = require_approval
    community.save()
    if require_approval:
        assert active_package_listing.is_waiting_for_approval == (
            review_status == PackageListingReviewStatus.unreviewed
        )
    else:
        assert active_package_listing.is_waiting_for_approval is False


@pytest.mark.django_db
@pytest.mark.parametrize("review_status", PackageListingReviewStatus.options())
def test_package_listing_is_rejected(
    active_package_listing: PackageListing,
    review_status: str,
) -> None:
    active_package_listing.review_status = review_status
    active_package_listing.save()
    assert active_package_listing.is_rejected is (
        review_status == PackageListingReviewStatus.rejected
    )


@pytest.mark.django_db
@pytest.mark.parametrize("require_approval", (False, True))
@pytest.mark.parametrize("review_status", PackageListingReviewStatus.options())
@pytest.mark.parametrize("user_type", TestUserTypes.options())
@pytest.mark.parametrize("team_role", TeamMemberRole.options() + [None])
@pytest.mark.parametrize("community_role", CommunityMemberRole.options() + [None])
def test_package_listing_ensure_can_be_viewed_by_user(
    active_package_listing: PackageListing,
    require_approval: bool,
    review_status: str,
    user_type: str,
    community_role: str,
    team_role: str,
):
    listing = active_package_listing
    listing.review_status = review_status
    listing.save()

    community = listing.community
    community.require_package_listing_approval = require_approval
    community.save()
    user = TestUserTypes.get_user_by_type(user_type)
    if community_role is not None and user_type not in TestUserTypes.fake_users():
        CommunityMembership.objects.create(
            user=user,
            community=community,
            role=community_role,
        )
    if team_role is not None and user_type not in TestUserTypes.fake_users():
        TeamMember.objects.create(
            user=user,
            team=listing.package.owner,
            role=team_role,
        )

    result = listing.can_be_viewed_by_user(user)
    errors = []
    expected_error = "Insufficient permissions to view"
    try:
        listing.ensure_can_be_viewed_by_user(user)
    except ValidationError as e:
        errors = e.messages

    if require_approval:
        if review_status == PackageListingReviewStatus.approved:
            assert result is True
            assert not errors
        elif user is None:
            assert result is False
            assert expected_error in errors
        elif not user.is_authenticated:
            assert result is False
            assert expected_error in errors
        elif community.can_user_manage_packages(user):
            assert result is True
            assert not errors
        elif listing.package.owner.can_user_access(user):
            assert result is True
            assert not errors
    else:
        if review_status != PackageListingReviewStatus.rejected:
            assert result is True
            assert not errors
        elif user is None:
            assert result is False
            assert expected_error in errors
        elif not user.is_authenticated:
            assert result is False
            assert expected_error in errors
        elif community.can_user_manage_packages(user):
            assert result is True
            assert not errors
        elif listing.package.owner.can_user_access(user):
            assert result is True
            assert not errors


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
@pytest.mark.parametrize("team_role", TeamMemberRole.options() + [None])
@pytest.mark.parametrize("community_role", CommunityMemberRole.options() + [None])
def test_package_listing_ensure_update_categories_permission(
    active_package_listing: PackageListing,
    user_type: str,
    community_role: str,
    team_role: str,
):
    listing = active_package_listing
    community = active_package_listing.community
    user = TestUserTypes.get_user_by_type(user_type)

    if community_role is not None and user_type not in TestUserTypes.fake_users():
        CommunityMembership.objects.create(
            user=user,
            community=community,
            role=community_role,
        )
    if team_role is not None and user_type not in TestUserTypes.fake_users():
        TeamMember.objects.create(
            user=user,
            team=listing.package.owner,
            role=team_role,
        )

    result = listing.check_update_categories_permission(user)
    errors = []
    try:
        listing.ensure_update_categories_permission(user)
    except ValidationError as e:
        errors = e.messages

    has_perms = any(
        (
            team_role == TeamMemberRole.owner,
            team_role == TeamMemberRole.member,
            community_role == CommunityMemberRole.owner,
            community_role == CommunityMemberRole.moderator,
        ),
    )

    error_map = {
        TestUserTypes.no_user: "Must be authenticated",
        TestUserTypes.unauthenticated: "Must be authenticated",
        TestUserTypes.regular_user: (
            None if has_perms else "Must have listing management permission"
        ),
        TestUserTypes.deactivated_user: "User has been deactivated",
        TestUserTypes.service_account: "Service accounts are unable to perform this action",
        TestUserTypes.site_admin: None,
        TestUserTypes.superuser: None,
    }
    expected_error = error_map[user_type]

    if expected_error:
        assert result is False
        assert len(errors) == 1
        assert errors[0] == expected_error
    else:
        assert result is True
        assert not errors


@pytest.mark.django_db
def test_package_listing_update_categories(
    active_package_listing: PackageListing,
    package_category: PackageCategory,
    team_owner: TeamMember,
    mocker,
):
    assert package_category.community == active_package_listing.community
    assert active_package_listing.package.owner == team_owner.team
    assert active_package_listing.categories.count() == 0
    mocked_permission_check = mocker.patch.object(
        active_package_listing,
        "ensure_update_categories_permission",
    )
    active_package_listing.update_categories(
        agent=team_owner.user,
        categories=[package_category],
    )
    mocked_permission_check.assert_called_with(team_owner.user)
    assert package_category in active_package_listing.categories.all()

    invalid_category = PackageCategory.objects.create(
        name="Test",
        slug="test",
        community=CommunityFactory(),
    )
    assert invalid_category.pk != package_category.pk
    with pytest.raises(
        ValidationError,
        match="Community mismatch between package listing and category",
    ):
        active_package_listing.update_categories(
            agent=team_owner.user,
            categories=[invalid_category],
        )


@pytest.mark.django_db
@pytest.mark.parametrize("require_approval", (False, True))
@pytest.mark.parametrize("review_status", PackageListingReviewStatus.options())
def test_package_listing_queryset_filter_by_community_approval_rule(
    require_approval: bool,
    review_status: str,
) -> None:
    PackageListingFactory(
        community_kwargs={"require_package_listing_approval": require_approval},
        review_status=review_status,
    )

    count = PackageListing.objects.filter_by_community_approval_rule().count()  # type: ignore

    if require_approval:
        if review_status == PackageListingReviewStatus.approved:
            assert count == 1
        else:
            assert count == 0
    else:
        if review_status == PackageListingReviewStatus.rejected:
            assert count == 0
        else:
            assert count == 1


@pytest.mark.django_db
def test_package_listing_filter_with_single_community_packages() -> None:
    communities = [
        CommunityFactory(aggregated_fields=CommunityAggregatedFields.objects.create())
        for _ in range(3)
    ]

    [PackageListingFactory(community_=community) for community in communities]

    for community in communities:
        CommunityAggregatedFields.update_for_community(community)
        count = community.package_listings.filter_with_single_community().count()
        assert count == 1
        assert community.aggregated.package_count == count


@pytest.mark.django_db
def test_package_listing_filter_with_multiple_community_packages() -> None:
    communities = [
        CommunityFactory(aggregated_fields=CommunityAggregatedFields.objects.create())
        for _ in range(3)
    ]

    # Setup a shared package listing for another community.
    shared_package = PackageVersionFactory().package
    extra_community = CommunityFactory(
        aggregated_fields=CommunityAggregatedFields.objects.create()
    )
    extra_listing = PackageListingFactory(
        community_=extra_community, package_=shared_package
    )

    # Add two package listings for each community, one with the shared package and one
    # with a unique package.
    for community in communities:
        PackageListingFactory(community_=community, package_=extra_listing.package)
        PackageListingFactory(community_=community)
        CommunityAggregatedFields.update_for_community(community)

    for community in communities:
        count = community.package_listings.filter_with_single_community().count()
        assert count == 1
        assert community.aggregated.package_count == count


@pytest.mark.django_db
@pytest.mark.parametrize("mod_manager_support", (False, True))
def test_package_listing_has_mod_manager_support(mod_manager_support: bool) -> None:
    community = CommunityFactory(has_mod_manager_support=mod_manager_support)
    package_listing = PackageListingFactory(community_=community)
    assert package_listing.has_mod_manager_support == mod_manager_support


@pytest.mark.django_db
def test_detect_and_assign_modpack_category() -> None:
    community = CommunityFactory()
    modpacks_category = PackageCategoryFactory(
        name="Modpacks", slug="modpacks", community=community
    )
    libraries_category = PackageCategoryFactory(
        name="Libraries", slug="libraries", community=community
    )

    version_with_dependencies = PackageVersionFactory()
    for _ in range(5):
        version_with_dependencies.dependencies.add(PackageVersionFactory())

    listing_with_dependencies = PackageListingFactory(
        package=version_with_dependencies.package, community=community
    )

    for version in version_with_dependencies.dependencies.all():
        PackageListingFactory(package=version.package, community=community)

    assert listing_with_dependencies.categories.all().count() == 0
    assert not listing_with_dependencies.categories.filter(slug="modpacks").exists()

    detect_and_assign_modpack_category(listing_with_dependencies.id)

    assert listing_with_dependencies.categories.all().count() == 1
    assert listing_with_dependencies.categories.filter(slug="modpacks").exists()

    # packages that depend on a lot of libraries shouldn't be given the modpack category

    version_with_libraries = PackageVersionFactory()
    for _ in range(5):
        version_with_libraries.dependencies.add(PackageVersionFactory())

    listing_with_libraries = PackageListingFactory(
        package=version_with_libraries.package, community=community
    )

    for version in version_with_libraries.dependencies.all():
        PackageListingFactory(
            package=version.package, community=community
        ).categories.add(libraries_category)

    detect_and_assign_modpack_category(listing_with_libraries.id)

    assert listing_with_libraries.categories.all().count() == 0
    assert not listing_with_libraries.categories.filter(slug="modpacks").exists()
