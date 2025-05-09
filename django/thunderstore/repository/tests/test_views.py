from typing import Any, Optional
from unittest import mock
from urllib import request

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import Http404
from django.test import Client
from django.urls import reverse
from rest_framework.test import APIClient

from conftest import TestUserTypes
from thunderstore.core.factories import UserFactory

from ...cache.enums import CacheBustCondition
from ...cache.tasks import invalidate_cache
from ...community.consts import PackageListingReviewStatus
from ...community.factories import CommunitySiteFactory, SiteFactory
from ...community.models import CommunitySite, PackageCategory, PackageListing
from ...core.types import UserType
from ...frontend.extract_props import extract_props_from_html
from ...frontend.url_reverse import get_community_url_reverse_args
from ..factories import PackageFactory, PackageVersionFactory, TeamFactory
from ..models import Package, Team, TeamMember, TeamMemberRole
from ..package_upload import PackageUploadForm
from ..views import PackageListByOwnerView, PackageVersionDetailView
from ..views.package._utils import can_view_listing_admin, can_view_package_admin


@pytest.mark.django_db
@pytest.mark.parametrize(
    "ordering", ("last-updated", "newest", "most-downloaded", "top-rated")
)
@pytest.mark.parametrize("old_urls", (False, True))
def test_package_list_view(client, community_site, ordering: str, old_urls: bool):
    for i in range(4):
        team = TeamFactory.create(
            name=f"Tester_{i}",
        )
        package = PackageFactory.create(
            owner=team,
            name=f"test_{i}",
            is_active=True,
            is_deprecated=False,
        )
        PackageVersionFactory.create(
            name=package.name,
            package=package,
            is_active=True,
        )
        PackageListing.objects.create(
            package=package,
            community=community_site.community,
        )

    for i in range(2):
        team = TeamFactory.create(
            name=f"RejectionTester_{i}",
        )
        package = PackageFactory.create(
            owner=team,
            name=f"test_rejected_{i}",
            is_active=True,
            is_deprecated=False,
        )
        PackageVersionFactory.create(
            name=package.name,
            package=package,
            is_active=True,
        )
        PackageListing.objects.create(
            package=package,
            community=community_site.community,
            review_status=PackageListingReviewStatus.rejected,
        )

    invalidate_cache(cache_bust_condition=CacheBustCondition.any_package_updated)

    if old_urls:
        base_url = reverse("old_urls:packages.list")
    else:
        base_url = reverse(
            "communities:community:packages.list",
            kwargs={"community_identifier": community_site.community.identifier},
        )
    url = f"{base_url}?ordering={ordering}"
    response = client.get(url, HTTP_HOST=community_site.site.domain)
    assert response.status_code == 200

    for i in range(4):
        assert f"test_{i}".encode("utf-8") in response.content

    bad_url = reverse(
        "communities:community:packages.list",
        kwargs={"community_identifier": "bad"},
    )
    response = client.get(bad_url, HTTP_HOST=community_site.site.domain)
    assert response.status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize("has_site", (True, False))
def test_package_list_search_view_get_breadcrumbs(
    active_package_listing: PackageListing,
    has_site: bool,
):
    community = active_package_listing.community
    if has_site:
        CommunitySiteFactory(community=community)
    owner = active_package_listing.package.owner
    mock_request = mock.Mock(spec=request.Request)
    mock_request.community = community

    kwargs = get_community_url_reverse_args(
        community=community, viewname="packages.list_by_owner", kwargs={"owner": owner}
    )["kwargs"]

    view = PackageListByOwnerView(kwargs=kwargs, request=mock_request)
    view.cache_owner()
    crumbs = view.get_breadcrumbs()

    if has_site:
        assert crumbs == [
            {"url": "/package/", "name": "Packages"},
            {"url": f"/package/{owner.name}/", "name": owner.name},
        ]
    else:
        assert crumbs == [
            {"url": f"/c/{community.identifier}/", "name": "Packages"},
            {"url": f"/c/{community.identifier}/p/{owner}/", "name": owner.name},
        ]


@pytest.mark.django_db
def test_package_detail_view(
    client, active_package_listing: PackageListing, community_site
):
    response = client.get(
        active_package_listing.get_absolute_url(),
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 200
    response_text = response.content.decode("utf-8")
    assert active_package_listing.package.name in response_text
    assert active_package_listing.package.owner.name in response_text


@pytest.mark.django_db
def test_package_detail_version_view(
    client, active_version_with_listing, community_site
):
    response = client.get(
        active_version_with_listing.get_absolute_url(),
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 200
    response_text = response.content.decode("utf-8")
    assert "Page not found" not in response_text
    assert active_version_with_listing.name in response_text
    assert active_version_with_listing.owner.name in response_text


@pytest.mark.django_db
def test_package_detail_version_view_cannot_be_viewed_by_user(
    client, team_member, active_version_with_listing, community_site
):
    community_site.community.require_package_listing_approval = True
    community_site.community.save()

    # Try with user that is member of owner team
    client.force_login(user=team_member.user)
    response = client.get(
        active_version_with_listing.get_absolute_url(),
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 200

    # Try with user that is not part of the owner team
    user = UserFactory.create()
    client.force_login(user=user)
    response = client.get(
        active_version_with_listing.get_absolute_url(),
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 404
    response_text = response.content.decode("utf-8")
    assert "Page not found" in response_text


@pytest.mark.django_db
def test_package_detail_version_view_can_be_viewed_by_user(
    client, team_member, active_version_with_listing, community_site
):
    community_site.community.require_package_listing_approval = True
    community_site.community.save()
    team_member.team = active_version_with_listing.owner
    team_member.save()

    client.force_login(user=team_member.user)
    response = client.get(
        active_version_with_listing.get_absolute_url(),
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 200
    response_text = response.content.decode("utf-8")
    assert "Page not found" not in response_text
    assert active_version_with_listing.name in response_text
    assert active_version_with_listing.owner.name in response_text


@pytest.mark.django_db
def test_package_detail_version_view_main_package_deactivated(
    client, active_version_with_listing, community_site
):
    active_version_with_listing.package.is_active = False
    active_version_with_listing.package.save()
    response = client.get(
        active_version_with_listing.get_absolute_url(),
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 404
    response_text = response.content.decode("utf-8")
    assert "Page not found" in response_text


@pytest.mark.django_db
def test_package_detail_version_view_get_object(
    active_version_with_listing, team_member, community_site
):
    owner = active_version_with_listing.package.owner
    name = active_version_with_listing.package.name
    version = active_version_with_listing
    mock_request = mock.Mock(spec=request.Request)
    mock_request.user = team_member.user
    mock_request.community = community_site.community
    view = PackageVersionDetailView(
        kwargs={"owner": owner, "name": name, "version": version}, request=mock_request
    )

    active_version_with_listing.package.is_active = False
    active_version_with_listing.package.save()
    with pytest.raises(Http404) as excinfo:
        view.get_object()
    assert "Main package is deactivated" in str(excinfo.value)

    # Remove user from view, so that the view doesn't have permissions to view the listing
    mock_request.user = None
    view = PackageVersionDetailView(
        kwargs={"owner": owner, "name": name, "version": version}, request=mock_request
    )
    community_site.community.require_package_listing_approval = True
    community_site.community.save()
    with pytest.raises(Http404) as excinfo:
        view.get_object()
    assert "Package is waiting for approval or has been rejected" in str(excinfo.value)


@pytest.mark.django_db
@pytest.mark.parametrize("old_urls", (False, True))
def test_package_create_view_not_logged_in(
    client, community_site: CommunitySite, old_urls: bool
):
    if old_urls:
        url = reverse("old_urls:packages.create")
    else:
        url = reverse(
            "communities:community:packages.create",
            kwargs={"community_identifier": community_site.community.identifier},
        )
    response = client.get(
        url,
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 302


@pytest.mark.django_db
@pytest.mark.parametrize("old_urls", (False, True))
def test_package_create_view_logged_in(
    client, community_site: CommunitySite, old_urls: bool
):
    user = UserFactory.create()
    client.force_login(user)
    if old_urls:
        url = reverse("old_urls:packages.create")
    else:
        url = reverse(
            "communities:community:packages.create",
            kwargs={"community_identifier": community_site.community.identifier},
        )
    response = client.get(
        url,
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 200
    assert b"Upload package" in response.content


@pytest.mark.django_db
@pytest.mark.parametrize("old_urls", (False, True))
def test_package_create_view_old_not_logged_in(
    client, community_site: CommunitySite, old_urls: bool
):
    if old_urls:
        url = reverse("old_urls:packages.create.old")
    else:
        url = reverse(
            "communities:community:packages.create.old",
            kwargs={"community_identifier": community_site.community.identifier},
        )
    response = client.get(
        url,
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 302


@pytest.mark.django_db
@pytest.mark.parametrize("old_urls", (False, True))
def test_package_create_view_old_logged_in(
    client, community_site: CommunitySite, old_urls: bool
):
    user = UserFactory.create()
    client.force_login(user)
    if old_urls:
        url = reverse("old_urls:packages.create.old")
    else:
        url = reverse(
            "communities:community:packages.create.old",
            kwargs={"community_identifier": community_site.community.identifier},
        )
    response = client.get(
        url,
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 200
    assert b"Upload package" in response.content


@pytest.mark.django_db
def test_package_download_view(
    user: UserType,
    client: Client,
    manifest_v1_package_bytes: bytes,
    settings: Any,
) -> None:
    primary_domain = "primary.example.org"
    community_domain_a = "community-a.example.org"
    community_domain_b = "community-b.example.org"
    primary_site = CommunitySiteFactory(site=SiteFactory(domain=primary_domain))
    package_site = CommunitySiteFactory(site=SiteFactory(domain=community_domain_a))
    random_site = CommunitySiteFactory(site=SiteFactory(domain=community_domain_b))
    assert community_domain_a != community_domain_b
    assert primary_domain != community_domain_a
    assert primary_domain != community_domain_b
    settings.PRIMARY_HOST = primary_domain
    settings.ALLOWED_HOSTS = [primary_domain, community_domain_a, community_domain_b]

    team = Team.get_or_create_for_user(user)
    file_data = {"file": SimpleUploadedFile("mod.zip", manifest_v1_package_bytes)}
    form = PackageUploadForm(
        user=user,
        files=file_data,
        community=package_site.community,
        data={
            "team": team.name,
            "communities": [package_site.community.identifier],
        },
    )
    assert form.is_valid()
    version = form.save()
    assert version.package.owner == team

    client.force_login(user)
    url = reverse(
        "old_urls:packages.download",
        kwargs={
            "owner": version.package.owner.name,
            "name": version.package.name,
            "version": version.version_number,
        },
    )

    # Should be accessible on the community's own domain
    response = client.get(url, HTTP_HOST=package_site.site.domain)
    assert response.status_code == 302
    assert response["Location"].startswith("http://minio:9000/")

    # Should be accessible in another community's domain
    response = client.get(url, HTTP_HOST=random_site.site.domain)
    assert response.status_code == 302
    assert response["Location"].startswith("http://minio:9000/")

    # Should be accessible on the primary domain
    response = client.get(url, HTTP_HOST=primary_site.site.domain)
    assert response.status_code == 302
    assert response["Location"].startswith("http://minio:9000/")


@pytest.mark.django_db
def test_service_account_list_view(client, community_site, team, team_member):
    client.force_login(team_member.user)
    kwargs = {"name": team.name}
    url = reverse("settings.teams.detail.service_accounts", kwargs=kwargs)
    response = client.get(url, HTTP_HOST=community_site.site.domain)
    assert response.status_code == 200
    assert f"Team {team.name} service accounts" in str(response.content)


@pytest.mark.django_db
def test_service_account_creation(client, community_site, team, team_owner):
    client.force_login(team_owner.user)
    kwargs = {"name": team.name}

    response = client.get(
        reverse("settings.teams.detail.add_service_account", kwargs=kwargs),
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 200
    assert b"Enter a nickname for the service account" in response.content

    response = client.post(
        reverse("settings.teams.detail.add_service_account", kwargs=kwargs),
        {"nickname": "Foo", "team": team.id},
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 200
    assert b'New service account <kbd class="text-info">Foo</kbd>' in response.content
    assert b'<pre class="important">tss_' in response.content


@pytest.mark.django_db
def test_team_creation_view(client, community_site, team_owner):
    client.force_login(team_owner.user)

    response = client.get(
        reverse("settings.teams.create"),
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 200
    assert b"Enter the name of the team you wish to create." in response.content

    response = client.post(
        reverse("settings.teams.create"),
        {"name": "TeamName"},
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 302


@pytest.mark.django_db
def test_team_settings_donation_link_view(
    client: APIClient,
    community_site: CommunitySite,
    team: Team,
    team_owner: TeamMember,
) -> None:
    client.force_login(team_owner.user)
    kwargs = {"name": team.name}

    response = client.get(
        reverse("settings.teams.detail.donation_link", kwargs=kwargs),
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 200
    assert b"You can configure a donation link for the team here." in response.content

    response = client.post(
        reverse("settings.teams.detail.donation_link", kwargs=kwargs),
        {"donation_link": "https://example.org/"},
        HTTP_HOST=community_site.site.domain,
        follow=True,
    )
    assert response.status_code == 200
    assert b"Donation link saved" in response.content


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
@pytest.mark.parametrize("role", TeamMemberRole.options() + [None])
def test_team_settings_donation_link_view_permissions(
    client: APIClient,
    community_site: CommunitySite,
    team: Team,
    user_type: str,
    role: Optional[str],
) -> None:
    valid_user_type_map = {
        TestUserTypes.no_user: False,
        TestUserTypes.unauthenticated: False,
        TestUserTypes.regular_user: True,
        TestUserTypes.deactivated_user: False,
        TestUserTypes.service_account: False,
        TestUserTypes.site_admin: True,
        TestUserTypes.superuser: True,
    }

    valid_role_map = {
        None: False,
        TeamMemberRole.member: False,
        TeamMemberRole.owner: True,
    }

    user = TestUserTypes.get_user_by_type(user_type)
    if role is not None and user_type not in TestUserTypes.fake_users():
        TeamMember.objects.create(user=user, team=team, role=role)
        client.force_login(user)

    should_succeed = all(
        (
            valid_user_type_map[user_type],
            valid_role_map[role],
        )
    )

    kwargs = {"name": team.name}
    response = client.post(
        reverse("settings.teams.detail.donation_link", kwargs=kwargs),
        {"donation_link": "https://example.org/"},
        HTTP_HOST=community_site.site.domain,
        follow=True,
    )

    if should_succeed:
        assert b"Donation link saved" in response.content
        team.refresh_from_db()
        assert team.donation_link == "https://example.org/"
    else:
        assert b"Donation link saved" not in response.content
        team.refresh_from_db()
        assert team.donation_link is None


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
def test_view_package_detail_management_option_visibility_without_team(
    client: APIClient,
    user_type: str,
    community_site: CommunitySite,
    active_package_listing: PackageListing,
    package_category: PackageCategory,
) -> None:
    assert community_site.community == active_package_listing.community
    assert package_category.community == active_package_listing.community
    active_package_listing.categories.add(package_category)

    user = TestUserTypes.get_user_by_type(user_type)
    if user_type not in TestUserTypes.fake_users():
        client.force_login(user)

    response = client.get(
        path=active_package_listing.get_absolute_url(),
        HTTP_HOST=community_site.site.domain,
    )

    expected_management_visibility = {
        TestUserTypes.no_user: False,
        TestUserTypes.unauthenticated: False,
        TestUserTypes.regular_user: False,
        TestUserTypes.deactivated_user: False,
        TestUserTypes.service_account: False,
        TestUserTypes.site_admin: True,
        TestUserTypes.superuser: True,
    }[user_type]
    expected_unlist_visibility = {
        TestUserTypes.no_user: False,
        TestUserTypes.unauthenticated: False,
        TestUserTypes.regular_user: False,
        TestUserTypes.deactivated_user: False,
        TestUserTypes.service_account: False,
        TestUserTypes.site_admin: False,
        TestUserTypes.superuser: True,
    }[user_type]

    expected = b'<div id="package-management-panel"></div>'
    if expected_management_visibility is False:
        assert expected not in response.content
    else:
        assert expected in response.content

    props = extract_props_from_html(
        html=response.content.decode(),
        component_name="PackageManagementPanel",
        component_id="package-management-panel",
    )
    if expected_management_visibility:
        assert props["canUnlist"] is expected_unlist_visibility
    else:
        assert props is None


@pytest.mark.django_db
@pytest.mark.parametrize("role", TeamMemberRole.options() + [None])
@pytest.mark.parametrize(
    "superuser",
    (
        False,
        True,
    ),
)
def test_view_package_detail_management_option_visibility_with_team(
    user: UserType,
    client: APIClient,
    community_site: CommunitySite,
    active_package_listing: PackageListing,
    package_category: PackageCategory,
    role: Optional[str],
    superuser: bool,
) -> None:
    assert community_site.community == active_package_listing.community
    assert package_category.community == active_package_listing.community
    active_package_listing.categories.add(package_category)

    client.force_login(user)
    if role is not None:
        TeamMember.objects.create(
            user=user,
            team=active_package_listing.package.owner,
            role=role,
        )
    if superuser:
        user.is_staff = True
        user.is_superuser = True
        user.save()

    response = client.get(
        path=active_package_listing.get_absolute_url(),
        HTTP_HOST=community_site.site.domain,
    )

    expected_management_visibility = {
        None: False,
        TeamMemberRole.owner: True,
        TeamMemberRole.member: True,
    }[role] or superuser is True

    expected = b'<div id="package-management-panel"></div>'
    if expected_management_visibility is False:
        assert expected not in response.content
    else:
        assert expected in response.content

    props = extract_props_from_html(
        html=response.content.decode(),
        component_name="PackageManagementPanel",
        component_id="package-management-panel",
    )
    if expected_management_visibility:
        assert props["canUnlist"] is superuser
    else:
        assert props is None


@pytest.mark.django_db
@pytest.mark.parametrize(
    "is_deprecated",
    (
        False,
        True,
    ),
)
def test_view_package_detail_management_deprecate(
    admin_client: APIClient,
    community_site: CommunitySite,
    active_package_listing: PackageListing,
    is_deprecated: bool,
) -> None:
    package = active_package_listing.package
    package.is_deprecated = is_deprecated
    package.save()

    response = admin_client.post(
        path=active_package_listing.get_absolute_url(),
        data={"deprecate": "Deprecate"},
        HTTP_HOST=community_site.site.domain,
    )
    if is_deprecated is False:
        assert response.status_code == 302
    else:
        assert response.status_code == 403
    package.refresh_from_db()
    assert package.is_deprecated is True


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
def test_view_package_detail_management_deprecate_permissions(
    client: APIClient,
    community_site: CommunitySite,
    active_package_listing: PackageListing,
    user_type: str,
) -> None:
    package = active_package_listing.package
    assert package.is_deprecated is False

    user = TestUserTypes.get_user_by_type(user_type)
    if user_type not in TestUserTypes.fake_users():
        client.force_login(user)

    response = client.post(
        path=active_package_listing.get_absolute_url(),
        data={"deprecate": "Deprecate"},
        HTTP_HOST=community_site.site.domain,
    )
    if user_type not in (TestUserTypes.superuser, TestUserTypes.site_admin):
        assert response.status_code == 403
        package.refresh_from_db()
        assert package.is_deprecated is False
    else:
        assert response.status_code == 302
        package.refresh_from_db()
        assert package.is_deprecated is True


@pytest.mark.django_db
@pytest.mark.parametrize(
    "is_deprecated",
    (
        False,
        True,
    ),
)
def test_view_package_detail_management_undeprecate(
    admin_client: APIClient,
    community_site: CommunitySite,
    active_package_listing: PackageListing,
    is_deprecated: bool,
) -> None:
    package = active_package_listing.package
    package.is_deprecated = is_deprecated
    package.save()

    response = admin_client.post(
        path=active_package_listing.get_absolute_url(),
        data={"undeprecate": "Undeprecate"},
        HTTP_HOST=community_site.site.domain,
    )
    if is_deprecated is True:
        assert response.status_code == 302
    else:
        assert response.status_code == 403
    package.refresh_from_db()
    assert package.is_deprecated is False


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
def test_view_package_detail_management_undeprecate_permissions(
    client: APIClient,
    community_site: CommunitySite,
    active_package_listing: PackageListing,
    user_type: str,
) -> None:
    package = active_package_listing.package
    package.is_deprecated = True
    package.save()
    package.refresh_from_db()
    assert package.is_deprecated is True

    user = TestUserTypes.get_user_by_type(user_type)
    if user_type not in TestUserTypes.fake_users():
        client.force_login(user)

    response = client.post(
        path=active_package_listing.get_absolute_url(),
        data={"undeprecate": "Undeprecate"},
        HTTP_HOST=community_site.site.domain,
    )
    if user_type not in (TestUserTypes.superuser, TestUserTypes.site_admin):
        assert response.status_code == 403
        package.refresh_from_db()
        assert package.is_deprecated is True
    else:
        assert response.status_code == 302
        package.refresh_from_db()
        assert package.is_deprecated is False


@pytest.mark.django_db
def test_view_package_detail_management_unlist(
    admin_client: APIClient,
    community_site: CommunitySite,
    active_package_listing: PackageListing,
) -> None:
    package = active_package_listing.package
    assert package.is_active is True

    response = admin_client.post(
        path=active_package_listing.get_absolute_url(),
        data={"unlist": "Unlist"},
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 302
    package.refresh_from_db()
    assert package.is_active is False


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
def test_view_package_detail_management_unlist_permissions(
    client: APIClient,
    community_site: CommunitySite,
    active_package_listing: PackageListing,
    user_type: str,
) -> None:
    package = active_package_listing.package
    assert package.is_active is True

    user = TestUserTypes.get_user_by_type(user_type)
    if user_type not in TestUserTypes.fake_users():
        client.force_login(user)

    response = client.post(
        path=active_package_listing.get_absolute_url(),
        data={"unlist": "Unlist"},
        HTTP_HOST=community_site.site.domain,
    )
    if user_type not in (TestUserTypes.superuser,):
        assert response.status_code == 403
        package.refresh_from_db()
        assert package.is_active is True
    else:
        assert response.status_code == 302
        package.refresh_from_db()
        assert package.is_active is False


User = get_user_model()


@pytest.mark.django_db
def test_view_package_detail_can_view_listing_admin(
    user: UserType,
    active_package_listing: PackageListing,
) -> None:
    assert can_view_listing_admin(user, active_package_listing) is False
    user.is_staff = True
    user.save()
    assert can_view_listing_admin(user, active_package_listing) is False
    content_type = ContentType.objects.get_for_model(PackageListing)
    permission = Permission.objects.get(
        codename="view_packagelisting",
        content_type=content_type,
    )
    user.user_permissions.add(permission)
    user = User.objects.get(pk=user.pk)  # Refresh permission cache
    assert can_view_listing_admin(user, active_package_listing) is True
    user.is_staff = False
    assert can_view_listing_admin(user, active_package_listing) is False


@pytest.mark.django_db
def test_view_package_detail_can_view_package_admin(
    user: UserType,
    active_package: Package,
) -> None:
    assert can_view_package_admin(user, active_package) is False
    user.is_staff = True
    user.save()
    assert can_view_package_admin(user, active_package) is False
    content_type = ContentType.objects.get_for_model(Package)
    permission = Permission.objects.get(
        codename="view_package",
        content_type=content_type,
    )
    user.user_permissions.add(permission)
    user = User.objects.get(pk=user.pk)  # Refresh permission cache
    assert can_view_package_admin(user, active_package) is True
    user.is_staff = False
    assert can_view_package_admin(user, active_package) is False
