from typing import Any

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from conftest import TestUserTypes
from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.factories import (
    CommunityFactory,
    PackageCategoryFactory,
    PackageListingFactory,
    SiteFactory,
)
from thunderstore.community.models.package_listing import PackageListing
from thunderstore.core.types import UserType
from thunderstore.repository.factories import PackageFactory, PackageVersionFactory
from thunderstore.repository.models import (
    Namespace,
    Package,
    PackageWiki,
    TeamMember,
    TeamMemberRole,
)
from thunderstore.wiki.factories import WikiPageFactory

User = get_user_model()


@pytest.mark.django_db
def test_package_get_page_url(
    active_package_listing: PackageListing,
) -> None:
    owner_url = active_package_listing.package.get_page_url(
        active_package_listing.community.identifier
    )
    assert owner_url == f"/c/test/p/Test_Team/{active_package_listing.package.name}/"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "site_host", ("thunderstore.dev", "test.thunderstore.dev", None)
)
@pytest.mark.parametrize(
    "primary_host", ("thunderstore.io", "stonderthure.io.example.org")
)
def test_package_get_full_url(
    settings: Any,
    site_host: str,
    primary_host: str,
    active_package: Package,
) -> None:
    site = SiteFactory(domain=site_host) if site_host is not None else None
    settings.PRIMARY_HOST = primary_host

    expected_host = site_host if site else primary_host
    expected_url = f"{settings.PROTOCOL}{expected_host}/package/{active_package.namespace.name}/{active_package.name}/"
    assert active_package.get_full_url(site=site) == expected_url


@pytest.mark.django_db
def test_package_deprecate() -> None:
    package: Package = PackageFactory(is_deprecated=False)
    old_updated = package.date_updated
    assert package.is_deprecated is False
    package.deprecate()
    assert package.is_deprecated is True
    assert package.date_updated == old_updated


@pytest.mark.django_db
def test_package_undeprecate() -> None:
    package: Package = PackageFactory(is_deprecated=True)
    old_updated = package.date_updated
    assert package.is_deprecated is True
    package.undeprecate()
    assert package.is_deprecated is False
    assert package.date_updated == old_updated


@pytest.mark.django_db
def test_package_deactivate() -> None:
    package = PackageFactory(is_active=True)
    old_updated = package.date_updated
    assert package.is_active is True
    package.deactivate()
    assert package.is_active is False
    assert package.date_updated == old_updated


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
@pytest.mark.parametrize("role", TeamMemberRole.options() + [None])
def test_package_ensure_user_can_manage_deprecation(
    namespace: Namespace, user_type: str, role: str
) -> None:
    user = TestUserTypes.get_user_by_type(user_type)
    team = namespace.team
    package = PackageFactory(owner=team, namespace=namespace)
    if role is not None and user_type not in TestUserTypes.fake_users():
        TeamMember.objects.create(user=user, team=team, role=role)

    if user_type in TestUserTypes.fake_users():
        expected_error = "Must be authenticated"
    elif user_type == TestUserTypes.deactivated_user:
        expected_error = "User has been deactivated"
    elif user_type in (TestUserTypes.site_admin, TestUserTypes.superuser):
        expected_error = None
    elif user_type == TestUserTypes.service_account:
        expected_error = "Service accounts are unable to perform this action"
    elif role in (TeamMemberRole.owner, TeamMemberRole.member):
        expected_error = None
    else:
        expected_error = "Must be a member of team to manage packages"

    if expected_error is not None:
        assert package.can_user_manage_deprecation(user) is False
        with pytest.raises(ValidationError, match=expected_error):
            package.ensure_user_can_manage_deprecation(user)
    else:
        assert package.can_user_manage_deprecation(user) is True
        assert package.ensure_user_can_manage_deprecation(user) is None


@pytest.mark.django_db
def test_package_ensure_user_can_manage_deprecation_deprecate_package_perm(
    namespace: Namespace,
    user: UserType,
):
    team = namespace.team
    package = PackageFactory(owner=team, namespace=namespace)
    user.is_staff = True
    user.save()
    assert package.can_user_manage_deprecation(user) is False
    content_type = ContentType.objects.get_for_model(Package)
    perm = Permission.objects.get(
        content_type=content_type, codename="deprecate_package"
    )
    user.user_permissions.add(perm)
    user = User.objects.get(pk=user.pk)
    assert package.can_user_manage_deprecation(user) is True


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
@pytest.mark.parametrize("role", TeamMemberRole.options() + [None])
def test_package_ensure_user_can_manage_wiki(
    namespace: Namespace, user_type: str, role: str
) -> None:
    user = TestUserTypes.get_user_by_type(user_type)
    team = namespace.team
    package = PackageFactory(owner=team, namespace=namespace)
    if role is not None and user_type not in TestUserTypes.fake_users():
        TeamMember.objects.create(user=user, team=team, role=role)

    if user_type in TestUserTypes.fake_users():
        expected_error = "Must be authenticated"
    elif user_type == TestUserTypes.deactivated_user:
        expected_error = "User has been deactivated"
    elif user_type == TestUserTypes.service_account:
        expected_error = "Service accounts are unable to perform this action"
    elif role in (TeamMemberRole.owner, TeamMemberRole.member):
        expected_error = None
    else:
        expected_error = "Must be a member of team to manage packages"

    if expected_error is not None:
        assert package.can_user_manage_wiki(user) is False
        with pytest.raises(ValidationError, match=expected_error):
            package.ensure_user_can_manage_wiki(user)
    else:
        assert package.can_user_manage_wiki(user) is True
        assert package.ensure_user_can_manage_wiki(user) is None


@pytest.mark.django_db
def test_package_has_wiki_no_wiki(package: Package) -> None:
    assert package.has_wiki is False


@pytest.mark.django_db
def test_package_has_wiki_no_pages(
    package: Package,
    package_wiki: PackageWiki,
) -> None:
    assert package_wiki.package == package
    assert package_wiki.wiki.pages.exists() is False
    assert package.has_wiki is False


@pytest.mark.django_db
def test_package_has_wiki_yes(
    package: Package,
    package_wiki: PackageWiki,
) -> None:
    assert package_wiki.package == package
    WikiPageFactory(wiki=package_wiki.wiki)
    assert package_wiki.wiki.pages.exists() is True
    assert package.has_wiki is True


@pytest.mark.django_db
def test_package_update_listing(
    active_package_listing: PackageListing,
):
    package = active_package_listing.package
    com = active_package_listing.community
    cats = [PackageCategoryFactory(community=com) for _ in range(3)]

    active_package_listing.categories.set([cats[0]])

    package.update_listing(
        has_nsfw_content=True,
        categories=[cats[1]],
        community=com,
    )
    listing = package.get_or_create_package_listing(com)
    assert listing.categories.count() == 2
    for entry in (cats[0], cats[1]):
        assert entry in listing.categories.all()

    package.update_listing(
        has_nsfw_content=True,
        categories=[cats[2]],
        community=com,
    )

    assert listing.categories.count() == 3
    for entry in cats:
        assert entry in listing.categories.all()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("package_is_active", "version_is_active", "expected_is_removed"),
    (
        (False, False, True),
        (True, False, True),
        (False, True, True),
        (True, True, False),
    ),
)
def test_package_is_removed(
    package_is_active: bool,
    version_is_active: bool,
    expected_is_removed: bool,
) -> None:
    package = PackageFactory(is_active=package_is_active)
    PackageVersionFactory(package=package, is_active=version_is_active)

    assert package.is_removed == expected_is_removed


@pytest.mark.django_db
@pytest.mark.parametrize(
    (
        "review_status",
        "package_is_active",
        "require_package_listing_approval",
        "expected_is_unavailable_result",
    ),
    [
        (PackageListingReviewStatus.approved, True, False, False),
        (PackageListingReviewStatus.approved, False, False, True),
        (PackageListingReviewStatus.rejected, True, False, True),
        (PackageListingReviewStatus.rejected, False, False, True),
        (PackageListingReviewStatus.unreviewed, True, True, True),
        (PackageListingReviewStatus.unreviewed, True, False, False),
        (PackageListingReviewStatus.unreviewed, False, True, True),
        (PackageListingReviewStatus.unreviewed, False, False, True),
    ],
)
def test_package_is_unavailable(
    review_status: PackageListingReviewStatus,
    package_is_active: bool,
    require_package_listing_approval: bool,
    expected_is_unavailable_result: bool,
) -> None:
    community = CommunityFactory(
        require_package_listing_approval=require_package_listing_approval
    )

    package = PackageFactory(is_active=package_is_active)
    if package_is_active:
        PackageVersionFactory(package=package, version_number="1.0.0")

    PackageListingFactory(
        package_=package,
        community_=community,
        review_status=review_status,
    )

    assert package.is_unavailable(community) == expected_is_unavailable_result


@pytest.mark.django_db
def test_package_is_unavailable_no_listing() -> None:
    community = CommunityFactory()
    package = PackageFactory(is_active=True)
    PackageVersionFactory(package=package, version_number="1.0.0")

    assert package.is_unavailable(community) is True


@pytest.mark.django_db
def test_package_is_unavailable_no_version() -> None:
    community = CommunityFactory()
    package = PackageFactory(is_active=True)
    PackageListingFactory(
        package_=package,
        community_=community,
        review_status=PackageListingReviewStatus.approved,
    )

    assert package.is_unavailable(community) is True
