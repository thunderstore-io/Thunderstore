from typing import Optional
from unittest.mock import PropertyMock, patch

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from conftest import TestUserTypes
from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.factories import (
    CommunityFactory,
    CommunitySiteFactory,
    PackageListingFactory,
    PackageVersionFactory,
)
from thunderstore.community.models import (
    AIDisclosure,
    Community,
    CommunityAggregatedFields,
    CommunityMemberRole,
    CommunityMembership,
    PackageCategory,
    PackageListing,
)
from thunderstore.core.factories import UserFactory
from thunderstore.permissions.models.tests._utils import (
    assert_default_visibility,
    assert_visibility_is_not_public,
    assert_visibility_is_not_visible,
    assert_visibility_is_public,
)
from thunderstore.repository.consts import PackageVersionReviewStatus
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
            community_role == CommunityMemberRole.janitor,
            community_role == CommunityMemberRole.moderator,
        ),
    )

    error_map = {
        TestUserTypes.no_user: "Must be authenticated",
        TestUserTypes.unauthenticated: "Must be authenticated",
        TestUserTypes.regular_user: (
            None if has_perms else "User is missing necessary roles or permissions"
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
def test_package_listing_queryset_active(
    active_package_listing: PackageListing,
) -> None:
    # Initially the active_package_listing should be in the active queryset
    assert PackageListing.objects.active().filter(pk=active_package_listing.pk).exists()

    # If the package is not active, it should be excluded
    package = active_package_listing.package
    package.is_active = False
    package.save()
    assert (
        not PackageListing.objects.active()
        .filter(pk=active_package_listing.pk)
        .exists()
    )

    # Revert package.is_active
    package.is_active = True
    package.save()
    assert PackageListing.objects.active().filter(pk=active_package_listing.pk).exists()

    # If the package has no active versions, it should be excluded
    package.versions.update(is_active=False)
    assert (
        not PackageListing.objects.active()
        .filter(pk=active_package_listing.pk)
        .exists()
    )


# TODO: Re-enable once visibility system fixed
# @pytest.mark.django_db
# def test_package_listing_visibility_inherits_package_is_active(
#     active_package_listing: PackageListing,
# ) -> None:
#     assert_visibility_is_public(active_package_listing.visibility)
#
#     package = active_package_listing.package
#
#     package.is_active = False
#     package.save()
#
#     active_package_listing.refresh_from_db()
#     assert_visibility_is_not_visible(active_package_listing.visibility)
#
#     package.is_active = True
#     package.save()
#
#     active_package_listing.refresh_from_db()
#     assert_visibility_is_public(active_package_listing.visibility)
#
#
# @pytest.mark.django_db
# def test_package_listing_visibility_inherits_union_of_package_versions_visibility(
#     active_package_listing: PackageListing,
# ) -> None:
#     assert_visibility_is_public(active_package_listing.visibility)
#
#     package = active_package_listing.package
#
#     for version in package.versions.all():
#         version.review_status = PackageVersionReviewStatus.rejected
#         version.save()
#
#     active_package_listing.refresh_from_db()
#     assert_visibility_is_not_public(active_package_listing.visibility)
#
#     for version in package.versions.all():
#         version.is_active = False
#         version.save()
#
#     active_package_listing.refresh_from_db()
#     assert_visibility_is_not_visible(active_package_listing.visibility)
#
#     for version in package.versions.all():
#         version.review_status = PackageVersionReviewStatus.approved
#         version.is_active = True
#         version.save()
#
#     active_package_listing.refresh_from_db()
#     assert_visibility_is_public(active_package_listing.visibility)
#
#
# @pytest.mark.django_db
# def test_set_visibility_from_review_status():
#     listing = PackageListingFactory()
#
#     listing.review_status = PackageListingReviewStatus.rejected
#     listing.set_visibility_from_review_status()
#     listing.visibility.save()
#
#     assert_visibility_is_not_public(listing.visibility)
#
#     listing.visibility.copy_from(listing.package.visibility)
#
#     listing.review_status = PackageListingReviewStatus.unreviewed
#     listing.set_visibility_from_review_status()
#     listing.visibility.save()
#
#     assert_default_visibility(listing.visibility)
#
#     listing.visibility.copy_from(listing.package.visibility)
#
#     listing.community.require_package_listing_approval = True
#     listing.set_visibility_from_review_status()
#     listing.visibility.save()
#
#     assert_visibility_is_not_public(listing.visibility)
#
#
# @pytest.mark.django_db
# def test_is_visible_to_user():
#     listing = PackageListingFactory()
#
#     user = UserFactory.create()
#
#     owner = UserFactory.create()
#     TeamMember.objects.create(
#         user=owner,
#         team=listing.package.owner,
#         role=TeamMemberRole.owner,
#     )
#
#     moderator = UserFactory.create()
#     CommunityMembership.objects.create(
#         user=moderator,
#         community=listing.community,
#         role=CommunityMemberRole.moderator,
#     )
#
#     admin = UserFactory.create(is_superuser=True)
#
#     agents = {
#         "anonymous": None,
#         "user": user,
#         "owner": owner,
#         "moderator": moderator,
#         "admin": admin,
#     }
#
#     flags = [
#         "public_detail",
#         "owner_detail",
#         "moderator_detail",
#         "admin_detail",
#     ]
#
#     # Admins are also moderators but not owners
#     expected = {
#         "public_detail": {
#             "anonymous": True,
#             "user": True,
#             "owner": True,
#             "moderator": True,
#             "admin": True,
#         },
#         "owner_detail": {
#             "anonymous": False,
#             "user": False,
#             "owner": True,
#             "moderator": False,
#             "admin": False,
#         },
#         "moderator_detail": {
#             "anonymous": False,
#             "user": False,
#             "owner": False,
#             "moderator": True,
#             "admin": True,
#         },
#         "admin_detail": {
#             "anonymous": False,
#             "user": False,
#             "owner": False,
#             "moderator": False,
#             "admin": True,
#         },
#     }
#
#     for flag in flags:
#         listing.visibility.public_detail = False
#         listing.visibility.owner_detail = False
#         listing.visibility.moderator_detail = False
#         listing.visibility.admin_detail = False
#
#         setattr(listing.visibility, flag, True)
#         listing.visibility.save()
#
#         for role, subject in agents.items():
#             result = listing.is_visible_to_user(subject)
#             assert result == expected[flag][role], (
#                 f"Expected {flag} visibility for {role} to be "
#                 f"{expected[flag][role]}, got {result}"
#             )
#
#     listing.visibility = None
#
#     assert not listing.is_visible_to_user(admin)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("is_rejected", "is_waiting_for_approval", "expected"),
    [(True, False, True), (False, True, True), (False, False, False)],
)
def test_package_listing_is_unavailable(
    is_rejected: bool,
    is_waiting_for_approval: bool,
    expected: bool,
) -> None:
    with patch(
        "thunderstore.community.models.PackageListing.is_rejected",
        new_callable=PropertyMock,
        return_value=is_rejected,
    ), patch(
        "thunderstore.community.models.PackageListing.is_waiting_for_approval",
        new_callable=PropertyMock,
        return_value=is_waiting_for_approval,
    ):

        listing = PackageListingFactory()
        assert listing.is_unavailable == expected


@pytest.mark.django_db
def test_package_listing_reject_or_approve_requires_permissions():
    listing = PackageListingFactory()
    user = UserFactory()

    with pytest.raises(PermissionError):
        listing.reject(
            agent=user, rejection_reason="Invalid submission", is_system=False
        )

    with pytest.raises(PermissionError):
        listing.approve(agent=user, is_system=False)

    user.is_superuser = True

    listing.reject(agent=user, rejection_reason="Invalid submission", is_system=False)

    assert listing.review_status == PackageListingReviewStatus.rejected

    listing.approve(agent=user, is_system=False)

    assert listing.review_status == PackageListingReviewStatus.approved


@pytest.mark.django_db
def test_package_listing_reject_or_approve_is_system_overrides_permissions():
    listing = PackageListingFactory()

    with pytest.raises(PermissionError):
        listing.reject(
            agent=None, rejection_reason="Invalid submission", is_system=False
        )

    with pytest.raises(PermissionError):
        listing.approve(agent=None, is_system=False)

    listing.reject(agent=None, rejection_reason="Invalid submission", is_system=True)

    assert listing.review_status == PackageListingReviewStatus.rejected

    listing.approve(agent=None, is_system=True)

    assert listing.review_status == PackageListingReviewStatus.approved


@pytest.mark.django_db
@pytest.mark.parametrize("should_fire", [True, False])
def test_package_listing_reject_audit_control(mocker, should_fire):
    listing = PackageListingFactory()
    mock_fire_audit = mocker.patch(
        "thunderstore.community.models.package_listing.fire_audit_event"
    )

    listing.reject(
        agent=None,
        rejection_reason="Invalid submission",
        is_system=True,
        should_fire_audit_event=should_fire,
    )

    assert mock_fire_audit.called is should_fire


@pytest.mark.django_db
def test_package_listing_reject_skips_notes_if_none():
    listing = PackageListingFactory()

    original_notes = "Original notes"
    listing.notes = original_notes
    listing.save()

    listing.reject(
        agent=None,
        rejection_reason="Invalid submission",
        is_system=True,
        internal_notes=None,
    )

    listing.refresh_from_db()
    assert listing.notes == original_notes


@pytest.mark.parametrize(
    "type_field",
    (
        "is_ai_generated",
        "is_ai_assisted",
        "has_ai_generated_art",
        "has_ai_generated_text",
    ),
)
@pytest.mark.parametrize(
    ("uses_ai", "has_type", "expected_error"),
    (
        (None, False, None),
        (False, False, None),
        (True, True, None),
        (True, False, "At least one type of AI usage must be selected"),
        (None, True, "Types of AI usage can only be selected when AI was used"),
        (False, True, "Types of AI usage can only be selected when AI was used"),
    ),
)
def test_ai_disclosure_validate(
    type_field: str,
    uses_ai: Optional[bool],
    has_type: bool,
    expected_error: Optional[str],
) -> None:
    disclosure = AIDisclosure(uses_ai=uses_ai, **{type_field: has_type})
    if expected_error:
        with pytest.raises(ValidationError, match=expected_error):
            disclosure.validate()
    else:
        disclosure.validate()


@pytest.mark.django_db
def test_package_listing_ai_disclosure_defaults(
    active_package_listing: PackageListing,
) -> None:
    assert active_package_listing.ai_disclosure == AIDisclosure()
    assert active_package_listing.ai_disclosure.uses_ai is None
    assert active_package_listing.is_ai_disclosure_locked is False


@pytest.mark.django_db
def test_package_listing_ai_disclosure_roundtrip(
    active_package_listing: PackageListing,
) -> None:
    disclosure = AIDisclosure(
        uses_ai=True,
        is_ai_assisted=True,
        has_ai_generated_art=True,
    )
    active_package_listing.ai_disclosure = disclosure
    active_package_listing.save()

    listing = PackageListing.objects.get(pk=active_package_listing.pk)
    assert listing.ai_disclosure == disclosure
    assert listing.uses_ai is True
    assert listing.is_ai_generated is False
    assert listing.is_ai_assisted is True
    assert listing.has_ai_generated_art is True
    assert listing.has_ai_generated_text is False


@pytest.mark.django_db
def test_package_listing_save_validates_ai_disclosure(
    active_package_listing: PackageListing,
) -> None:
    active_package_listing.is_ai_generated = True
    with pytest.raises(ValidationError, match="Types of AI usage can only be"):
        active_package_listing.save()

    active_package_listing.uses_ai = True
    active_package_listing.save()


@pytest.mark.django_db
@pytest.mark.parametrize("is_locked", (False, True))
@pytest.mark.parametrize("user_type", TestUserTypes.options())
@pytest.mark.parametrize("team_role", TeamMemberRole.options() + [None])
@pytest.mark.parametrize("community_role", CommunityMemberRole.options() + [None])
def test_package_listing_ensure_update_ai_disclosure_permission(
    active_package_listing: PackageListing,
    is_locked: bool,
    user_type: str,
    community_role: str,
    team_role: str,
):
    listing = active_package_listing
    listing.is_ai_disclosure_locked = is_locked
    listing.save()
    user = TestUserTypes.get_user_by_type(user_type)

    if community_role is not None and user_type not in TestUserTypes.fake_users():
        CommunityMembership.objects.create(
            user=user,
            community=listing.community,
            role=community_role,
        )
    if team_role is not None and user_type not in TestUserTypes.fake_users():
        TeamMember.objects.create(
            user=user,
            team=listing.package.owner,
            role=team_role,
        )

    result = listing.check_update_ai_disclosure_permission(user)
    errors = []
    try:
        listing.ensure_update_ai_disclosure_permission(user)
    except ValidationError as e:
        errors = e.messages

    is_moderator = community_role in (
        CommunityMemberRole.owner,
        CommunityMemberRole.moderator,
    )
    if is_moderator:
        regular_user_error = None
    elif team_role is None:
        regular_user_error = "Must have listing management permission"
    elif is_locked:
        regular_user_error = "AI disclosure has been locked by a moderator"
    else:
        regular_user_error = None

    error_map = {
        TestUserTypes.no_user: "Must be authenticated",
        TestUserTypes.unauthenticated: "Must be authenticated",
        TestUserTypes.regular_user: regular_user_error,
        TestUserTypes.deactivated_user: "User has been deactivated",
        TestUserTypes.service_account: "Service accounts are unable to perform this action",
        TestUserTypes.site_admin: None,
        TestUserTypes.superuser: None,
    }
    expected_error = error_map[user_type]

    if expected_error:
        assert result is False
        assert errors == [expected_error]
    else:
        assert result is True
        assert not errors


@pytest.mark.django_db
def test_package_listing_update_ai_disclosure(
    active_package_listing: PackageListing,
    team_owner: TeamMember,
) -> None:
    disclosure = AIDisclosure(uses_ai=True, has_ai_generated_text=True)
    active_package_listing.update_ai_disclosure(
        agent=team_owner.user,
        disclosure=disclosure,
    )
    listing = PackageListing.objects.get(pk=active_package_listing.pk)
    assert listing.ai_disclosure == disclosure

    no_ai = AIDisclosure(uses_ai=False)
    active_package_listing.update_ai_disclosure(agent=team_owner.user, disclosure=no_ai)
    listing = PackageListing.objects.get(pk=active_package_listing.pk)
    assert listing.ai_disclosure == no_ai


@pytest.mark.django_db
def test_package_listing_update_ai_disclosure_rejects_invalid(
    active_package_listing: PackageListing,
    team_owner: TeamMember,
) -> None:
    with pytest.raises(ValidationError, match="At least one type of AI usage"):
        active_package_listing.update_ai_disclosure(
            agent=team_owner.user,
            disclosure=AIDisclosure(uses_ai=True),
        )
    listing = PackageListing.objects.get(pk=active_package_listing.pk)
    assert listing.ai_disclosure == AIDisclosure()


@pytest.mark.django_db
def test_package_listing_update_ai_disclosure_respects_lock(
    active_package_listing: PackageListing,
    team_owner: TeamMember,
) -> None:
    moderator = UserFactory()
    CommunityMembership.objects.create(
        user=moderator,
        community=active_package_listing.community,
        role=CommunityMemberRole.moderator,
    )
    moderated = AIDisclosure(uses_ai=True, is_ai_generated=True)
    active_package_listing.update_ai_disclosure(agent=moderator, disclosure=moderated)
    active_package_listing.set_ai_disclosure_lock(agent=moderator, is_locked=True)

    with pytest.raises(
        ValidationError,
        match="AI disclosure has been locked by a moderator",
    ):
        active_package_listing.update_ai_disclosure(
            agent=team_owner.user,
            disclosure=AIDisclosure(uses_ai=False),
        )
    listing = PackageListing.objects.get(pk=active_package_listing.pk)
    assert listing.ai_disclosure == moderated
    assert listing.is_ai_disclosure_locked is True

    active_package_listing.set_ai_disclosure_lock(agent=moderator, is_locked=False)
    active_package_listing.update_ai_disclosure(
        agent=team_owner.user,
        disclosure=AIDisclosure(uses_ai=False),
    )
    listing = PackageListing.objects.get(pk=active_package_listing.pk)
    assert listing.ai_disclosure == AIDisclosure(uses_ai=False)
    assert listing.is_ai_disclosure_locked is False


@pytest.mark.django_db
def test_package_listing_set_ai_disclosure_lock_requires_moderator(
    active_package_listing: PackageListing,
    team_owner: TeamMember,
) -> None:
    with pytest.raises(
        ValidationError,
        match="Must be a moderator or higher to manage packages",
    ):
        active_package_listing.set_ai_disclosure_lock(
            agent=team_owner.user,
            is_locked=True,
        )
    listing = PackageListing.objects.get(pk=active_package_listing.pk)
    assert listing.is_ai_disclosure_locked is False
