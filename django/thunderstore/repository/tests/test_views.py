import pytest

from django.urls import reverse

from thunderstore.core.factories import UserFactory

from ..factories import UploaderIdentityFactory
from ..factories import PackageFactory
from ..factories import PackageVersionFactory
from ...community.models import PackageListing


@pytest.mark.django_db
def test_package_list_view(client, community_site):
    for i in range(4):
        uploader = UploaderIdentityFactory.create(
            name=f"Tester-{i}",
        )
        package = PackageFactory.create(
            owner=uploader,
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
    response = client.get(reverse("packages.list"), HTTP_HOST=community_site.site.domain)
    assert response.status_code == 200

    for i in range(4):
        assert f"test_{i}".encode("utf-8") in response.content


@pytest.mark.django_db
def test_package_detail_view(client, active_package, community_site):
    response = client.get(active_package.get_absolute_url(), HTTP_HOST=community_site.site.domain)
    assert response.status_code == 200
    response_text = response.content.decode("utf-8")
    assert active_package.name in response_text
    assert active_package.owner.name in response_text


@pytest.mark.django_db
def test_package_detail_version_view(client, active_version, community_site):
    response = client.get(active_version.get_absolute_url(), HTTP_HOST=community_site.site.domain)
    assert response.status_code == 200
    response_text = response.content.decode("utf-8")
    assert active_version.name in response_text
    assert active_version.owner.name in response_text


@pytest.mark.django_db
def test_package_create_view_not_logged_in(client, community_site):
    response = client.get(reverse("packages.create"), HTTP_HOST=community_site.site.domain)
    assert response.status_code == 302


@pytest.mark.django_db
def test_package_create_view_logged_in(client, community_site):
    user = UserFactory.create()
    client.force_login(user)
    response = client.get(reverse("packages.create"), HTTP_HOST=community_site.site.domain)
    assert response.status_code == 200
    assert b"Upload package" in response.content
