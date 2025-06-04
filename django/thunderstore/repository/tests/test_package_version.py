from typing import Any, Literal, Union

import pytest
from django.contrib.auth.models import AnonymousUser
from django.db import IntegrityError

from thunderstore.community.factories import CommunityFactory, PackageListingFactory
from thunderstore.community.models import CommunityMemberRole, CommunityMembership
from thunderstore.community.models.package_listing import PackageListing
from thunderstore.core.factories import UserFactory
from thunderstore.permissions.models.tests._utils import (
    assert_visibility_is_not_public,
    assert_visibility_is_not_visible,
)
from thunderstore.repository.consts import PackageVersionReviewStatus
from thunderstore.repository.factories import PackageFactory, PackageVersionFactory
from thunderstore.repository.models import PackageVersion, TeamMember, TeamMemberRole
from thunderstore.repository.package_formats import PackageFormats
from thunderstore.webhooks.audit import AuditAction, AuditTarget


@pytest.mark.django_db
def test_get_total_used_disk_space():
    assert PackageVersion.get_total_used_disk_space() == 0
    p1 = PackageVersionFactory.create()
    assert PackageVersion.get_total_used_disk_space() == p1.file_size
    p2 = PackageVersionFactory.create(file_size=212312412)
    assert PackageVersion.get_total_used_disk_space() == p1.file_size + p2.file_size


@pytest.mark.django_db
def test_package_version_queryset_active():
    p1 = PackageVersionFactory(is_active=True)
    p2 = PackageVersionFactory(is_active=False)

    active_versions = PackageVersion.objects.active()
    assert p1 in active_versions
    assert p2 not in active_versions


@pytest.mark.django_db
def test_package_version_queryset_listed_in():
    l1 = PackageListingFactory()
    l2 = PackageListingFactory()
    l3 = PackageListingFactory()

    versions1 = PackageVersion.objects.listed_in(l1.community.identifier)
    versions2 = PackageVersion.objects.listed_in(l2.community.identifier)

    assert l1.package.latest in versions1
    assert l1.package.latest not in versions2
    assert l2.package.latest not in versions1
    assert l2.package.latest in versions2
    assert l3.package.latest not in versions1
    assert l3.package.latest not in versions2


@pytest.mark.django_db
def test_package_version_get_page_url(
    active_package_listing: PackageListing,
) -> None:
    owner_url = active_package_listing.package.latest.get_page_url(
        active_package_listing.community.identifier,
    )
    assert (
        owner_url
        == f"/c/test/p/Test_Team/{active_package_listing.package.name}/v/{active_package_listing.package.latest.version_number}/"
    )


@pytest.mark.django_db
@pytest.mark.parametrize("protocol", ("http://", "https://"))
@pytest.mark.parametrize(
    "primary_host",
    ("primary.example.org", "secondary.example.org"),
)
def test_package_version_full_download_url(
    active_package_listing: PackageListing,
    protocol: str,
    primary_host: str,
    settings: Any,
) -> None:
    settings.PRIMARY_HOST = primary_host
    settings.PROTOCOL = protocol
    package = active_package_listing.package
    namespace = package.namespace.name
    version = package.latest
    expected = f"{protocol}{primary_host}/package/download/{namespace}/{package.name}/{version.version_number}/"
    assert version.full_download_url == expected


@pytest.mark.django_db
@pytest.mark.parametrize("format_spec", PackageFormats.values + [None, "invalid"])
def test_package_version_format_spec_constraint(
    package_version: PackageVersion,
    format_spec: Union[PackageFormats, None, Literal["invalid"]],
) -> None:
    package_version.format_spec = format_spec
    should_pass = format_spec != "invalid"
    if should_pass:
        package_version.save()
    else:
        with pytest.raises(
            IntegrityError,
            match='violates check constraint "valid_package_format"',
        ):
            package_version.save()


@pytest.mark.django_db
def test_package_version_chunked_enumerate() -> None:
    package_ids = {PackageVersionFactory().pk for _ in range(10)}

    assert len(package_ids) == 10
    assert PackageVersion.objects.count() == 10

    for entry in PackageVersion.objects.chunked_enumerate(3):
        package_ids.remove(entry.pk)

    assert len(package_ids) == 0


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
def test_package_version_is_effectively_active(
    package_is_active: bool,
    version_is_active: bool,
) -> None:
    package = PackageFactory(is_active=package_is_active)
    version = PackageVersionFactory(package=package, is_active=version_is_active)

    assert version.is_effectively_active == (package_is_active and version_is_active)


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
def test_package_version_is_removed(
    package_is_active: bool,
    version_is_active: bool,
    expected_is_removed: bool,
) -> None:
    package = PackageFactory(is_active=package_is_active)
    version = PackageVersionFactory(package=package, is_active=version_is_active)

    assert version.is_removed == expected_is_removed


@pytest.mark.django_db
def test_package_version_build_audit_event():
    version = PackageVersionFactory()

    target = AuditTarget.VERSION
    action = AuditAction.REJECTED
    user_id = UserFactory().pk
    message = "Rejected a version"

    audit_event = version.build_audit_event(
        action=action,
        user_id=user_id,
        message=message,
    )

    assert audit_event.target == target
    assert audit_event.action == action
    assert audit_event.user_id == user_id
    assert audit_event.message == message
    assert audit_event.related_url == version.package.get_view_on_site_url()
    assert audit_event.fields[0].name == "Package"
    assert audit_event.fields[0].value == version.package.full_package_name


@pytest.mark.django_db
def test_reject_or_approve_requires_permissions():
    version = PackageVersionFactory()
    user = UserFactory()

    with pytest.raises(PermissionError):
        version.reject(agent=user, is_system=False)

    with pytest.raises(PermissionError):
        version.approve(agent=user, is_system=False)

    user.is_superuser = True

    version.reject(agent=user, is_system=False)

    assert version.review_status == PackageVersionReviewStatus.rejected

    version.approve(agent=user, is_system=False)

    assert version.review_status == PackageVersionReviewStatus.approved


@pytest.mark.django_db
def test_reject_or_approve_requires_is_system_overrides_permissions():
    version = PackageVersionFactory()

    with pytest.raises(PermissionError):
        version.reject(agent=None, is_system=False)

    with pytest.raises(PermissionError):
        version.approve(agent=None, is_system=False)

    version.reject(agent=None, is_system=True)

    assert version.review_status == PackageVersionReviewStatus.rejected

    version.approve(agent=None, is_system=True)

    assert version.review_status == PackageVersionReviewStatus.approved


@pytest.mark.django_db
def test_set_visibility_from_active_status_inactive_version():
    version = PackageVersionFactory()
    version.is_active = False
    version.set_visibility_from_active_status()
    version.visibility.save()
    assert_visibility_is_not_visible(version.visibility)


@pytest.mark.django_db
def test_set_visibility_from_active_status_inactive_package():
    version = PackageVersionFactory()
    version.package.is_active = False
    version.set_visibility_from_active_status()
    version.visibility.save()
    assert_visibility_is_not_visible(version.visibility)


@pytest.mark.django_db
def test_set_visibility_from_review_status():
    version = PackageVersionFactory()

    version.review_status = PackageVersionReviewStatus.rejected
    version.set_visibility_from_review_status()
    version.visibility.save()
    assert_visibility_is_not_public(version.visibility)


@pytest.mark.django_db
def test_can_user_manage_approval_status_false_if_unauthenticated():
    unauthenticated_user = AnonymousUser()

    version = PackageVersionFactory()

    assert not version.can_user_manage_approval_status(unauthenticated_user)
    assert not version.can_user_manage_approval_status(None)


# TODO: Re-enable once visibility system fixed
# @pytest.mark.django_db
# def test_is_visible_to_user():
#     version = PackageVersionFactory()
#     listing = PackageListingFactory(package=version.package)
#
#     user = UserFactory.create()
#
#     owner = UserFactory.create()
#     TeamMember.objects.create(
#         user=owner,
#         team=version.package.owner,
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
#         version.visibility.public_detail = False
#         version.visibility.owner_detail = False
#         version.visibility.moderator_detail = False
#         version.visibility.admin_detail = False
#
#         setattr(version.visibility, flag, True)
#         version.visibility.save()
#
#         for role, subject in agents.items():
#             result = version.is_visible_to_user(subject)
#             assert result == expected[flag][role], (
#                 f"Expected {flag} visibility for {role} to be "
#                 f"{expected[flag][role]}, got {result}"
#             )
#
#     version.visibility = None
#
#     assert not version.is_visible_to_user(admin)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("package_is_unavailable", "version_is_active", "expected_is_unavailable"),
    [
        (True, True, True),
        (True, False, True),
        (False, True, False),
        (False, False, True),
    ],
)
def test_package_version_is_unavailable(
    package_is_unavailable: bool,
    version_is_active: bool,
    expected_is_unavailable: bool,
) -> None:
    community = CommunityFactory()
    package = PackageFactory()
    package.is_unavailable = lambda _: package_is_unavailable
    version = PackageVersionFactory(package=package, is_active=version_is_active)

    assert version.is_unavailable(community) == expected_is_unavailable
