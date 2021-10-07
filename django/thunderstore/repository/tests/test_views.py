from unittest import mock
from urllib import request

import pytest
from django.contrib.sites.models import Site
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.http import Http404
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from thunderstore.core.factories import UserFactory

from ...community.models import (
    Community,
    CommunitySite,
    PackageListing,
    PackageListingReviewStatus,
)
from ..factories import PackageFactory, PackageVersionFactory, TeamFactory
from ..models import Team
from ..package_upload import PackageUploadForm
from ..views.repository import (
    PackageDetailView,
    PackageListSearchView,
    PackageVersionDetailView,
)


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

    base_url = reverse("packages.list")
    url = f"{base_url}?ordering={ordering}"
    response = client.get(url, HTTP_HOST=community_site.site.domain)
    assert response.status_code == 200

    for i in range(4):
        assert f"test_{i}".encode("utf-8") in response.content


@pytest.mark.django_db
def test_package_list_search_view_get_page_title():
    assert PackageListSearchView().get_page_title() == ""


@pytest.mark.django_db
def test_package_list_search_view_get_cache_vary():
    assert PackageListSearchView().get_cache_vary() == ""


@override_settings(ALLOWED_HOSTS=["testsite.test", "testsite2.test"])
@pytest.mark.django_db
def test_package_detail_view_community_redirect(
    client, active_package_listing, community_site
):
    community_2 = Community.objects.create(name="Test2", identifier="test2")
    site_2 = Site.objects.create(domain="testsite2.test", name="Testsite2")
    community_site_2 = CommunitySite.objects.create(site=site_2, community=community_2)
    response = client.get(
        active_package_listing.package.get_absolute_url(),
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 200
    response_text = response.content.decode("utf-8")
    assert active_package_listing.package.name in response_text
    assert active_package_listing.package.owner.name in response_text
    response = client.get(
        active_package_listing.package.get_absolute_url(),
        HTTP_HOST=community_site_2.site.domain,
    )
    assert response.status_code == 302


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
def test_package_detail_view_get_object(
    active_package_listing, team_member, community_site
):
    owner = active_package_listing.package.owner
    name = active_package_listing.package.name
    mock_request = mock.Mock(spec=request.Request)
    mock_request.user = team_member.user
    mock_request.community = community_site.community
    view = PackageDetailView(
        kwargs={"owner": owner, "name": name},
        request=mock_request,
    )
    obj = view.get_object()
    assert active_package_listing == obj

    mock_request.community.require_package_listing_approval = True
    mock_request.community.save()
    active_package_listing.review_status = PackageListingReviewStatus.rejected
    active_package_listing.save()
    mock_request.user = None
    view = PackageDetailView(
        kwargs={"owner": owner, "name": name},
        request=mock_request,
    )
    view.get_object.cache_clear()
    with pytest.raises(Http404) as exc:
        view.get_object()
    assert "Package is waiting for approval or has been rejected" in str(exc.value)


@override_settings(ALLOWED_HOSTS=["testsite.test", "testsite2.test"])
@pytest.mark.django_db
def test_package_detail_version_view_community_redirect(
    client, active_version_with_listing, community_site
):
    community_2 = Community.objects.create(name="Test2", identifier="test2")
    site_2 = Site.objects.create(domain="testsite2.test", name="Testsite2")
    community_site_2 = CommunitySite.objects.create(site=site_2, community=community_2)
    response = client.get(
        active_version_with_listing.package.versions.first().get_absolute_url(),
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 200
    response_text = response.content.decode("utf-8")
    assert active_version_with_listing.package.name in response_text
    assert active_version_with_listing.package.owner.name in response_text
    response = client.get(
        active_version_with_listing.package.versions.first().get_absolute_url(),
        HTTP_HOST=community_site_2.site.domain,
    )
    assert response.status_code == 302


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

    client.force_login(user=team_member.user)
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
        kwargs={"owner": owner, "name": name, "version": version.version_number},
        request=mock_request,
    )
    assert view.get_object() == active_version_with_listing


@pytest.mark.django_db
def test_package_detail_version_view_get_object_and_listing(
    active_version_with_listing, team_member, community_site
):
    owner = active_version_with_listing.package.owner
    name = active_version_with_listing.package.name
    version = active_version_with_listing
    mock_request = mock.Mock(spec=request.Request)
    mock_request.user = team_member.user
    mock_request.community = community_site.community
    view = PackageVersionDetailView(
        kwargs={"owner": owner, "name": name, "version": version.version_number},
        request=mock_request,
    )

    found_version, listing = view.get_object_and_listing()
    assert found_version == version

    active_version_with_listing.is_active = False
    active_version_with_listing.save()
    view.get_object_and_listing.cache_clear()
    with pytest.raises(Http404) as excinfo:
        view.get_object_and_listing()
    assert "No matching package found" in str(excinfo.value)
    active_version_with_listing.is_active = True
    active_version_with_listing.save()

    active_version_with_listing.package.is_active = False
    active_version_with_listing.package.save()
    view.get_object_and_listing.cache_clear()
    with pytest.raises(Http404) as excinfo:
        view.get_object_and_listing()
    assert "No matching package found" in str(excinfo.value)
    active_version_with_listing.package.is_active = True
    active_version_with_listing.package.save()

    community_site.community.require_package_listing_approval = True
    community_site.community.save()
    view.get_object_and_listing.cache_clear()
    with pytest.raises(Http404) as excinfo:
        view.get_object_and_listing()
    assert "Package is waiting for approval or has been rejected" in str(excinfo.value)


@override_settings(DEBUG=True)
@pytest.mark.django_db
def test_package_detail_version_view_get_object_and_listing_cache(
    active_version_with_listing, team_member, community_site
):
    owner = active_version_with_listing.package.owner
    name = active_version_with_listing.package.name
    version = active_version_with_listing
    mock_request = mock.Mock(spec=request.Request)
    mock_request.user = team_member.user
    mock_request.community = community_site.community
    view = PackageVersionDetailView(
        kwargs={"owner": owner, "name": name, "version": version.version_number},
        request=mock_request,
    )
    PackageVersionFactory.create(
        name=active_version_with_listing.package.name,
        package=active_version_with_listing.package,
        is_active=True,
        version_number="2.0.0",
    )
    second_view = PackageVersionDetailView(
        kwargs={"owner": owner, "name": name, "version": "2.0.0"},
        request=mock_request,
    )

    with CaptureQueriesContext(connection) as queries:
        found_version, listing = view.get_object_and_listing()
    assert found_version == version
    assert len(queries.captured_queries) > 0

    with CaptureQueriesContext(connection) as queries:
        found_version, listing = view.get_object_and_listing()
    assert found_version == version
    assert len(queries.captured_queries) == 0

    with CaptureQueriesContext(connection) as queries:
        found_second_version, listing = second_view.get_object_and_listing()
    assert found_second_version.version_number == "2.0.0"
    assert len(queries.captured_queries) > 0

    with CaptureQueriesContext(connection) as queries:
        found_second_version, listing = second_view.get_object_and_listing()
    assert found_second_version.version_number == "2.0.0"
    assert len(queries.captured_queries) == 0


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
