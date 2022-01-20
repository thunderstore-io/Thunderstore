from unittest import mock
from urllib import request

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import Http404
from django.urls import reverse

from thunderstore.core.factories import UserFactory

from ...cache.cache import CacheBustCondition
from ...cache.tasks import invalidate_cache
from ...community.models import PackageListing, PackageListingReviewStatus
from ..factories import PackageFactory, PackageVersionFactory, TeamFactory
from ..models import Team
from ..package_upload import PackageUploadForm
from ..views.repository import PackageVersionDetailView


@pytest.mark.django_db
@pytest.mark.parametrize(
    "ordering", ("last-updated", "newest", "most-downloaded", "top-rated")
)
def test_package_list_view(client, community_site, ordering):
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

    base_url = reverse("packages.list")
    url = f"{base_url}?ordering={ordering}"
    response = client.get(url, HTTP_HOST=community_site.site.domain)
    assert response.status_code == 200

    for i in range(4):
        assert f"test_{i}".encode("utf-8") in response.content


@pytest.mark.django_db
def test_package_detail_view(
    client, active_package_listing: PackageListing, community_site
):
    response = client.get(
        active_package_listing.package.get_absolute_url(),
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
def test_package_create_view_not_logged_in(client, community_site):
    response = client.get(
        reverse("packages.create"), HTTP_HOST=community_site.site.domain
    )
    assert response.status_code == 302


@pytest.mark.django_db
def test_package_create_view_logged_in(client, community_site):
    user = UserFactory.create()
    client.force_login(user)
    response = client.get(
        reverse("packages.create"), HTTP_HOST=community_site.site.domain
    )
    assert response.status_code == 200
    assert b"Upload package" in response.content


@pytest.mark.django_db
def test_package_create_view_old_not_logged_in(client, community_site):
    response = client.get(
        reverse("packages.create.old"),
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 302


@pytest.mark.django_db
def test_package_create_view_old_logged_in(client, community_site):
    user = UserFactory.create()
    client.force_login(user)
    response = client.get(
        reverse("packages.create.old"),
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 200
    assert b"Upload package" in response.content


@pytest.mark.django_db
def test_package_download_view(user, client, community_site, manifest_v1_package_bytes):
    team = Team.get_or_create_for_user(user)
    file_data = {"file": SimpleUploadedFile("mod.zip", manifest_v1_package_bytes)}
    form = PackageUploadForm(
        user=user,
        files=file_data,
        community=community_site.community,
        data={
            "team": team.name,
            "communities": [community_site.community.identifier],
        },
    )
    assert form.is_valid()
    version = form.save()
    assert version.package.owner == team

    client.force_login(user)
    response = client.get(
        reverse(
            "packages.download",
            kwargs={
                "owner": version.package.owner.name,
                "name": version.package.name,
                "version": version.version_number,
            },
        ),
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 302


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
