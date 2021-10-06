import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from thunderstore.core.factories import UserFactory

from ...community.models import PackageListing, PackageListingReviewStatus
from ..factories import PackageFactory, PackageVersionFactory, UploaderIdentityFactory
from ..models import UploaderIdentity
from ..package_upload import PackageUploadForm


@pytest.mark.django_db
@pytest.mark.parametrize(
    "ordering", ("last-updated", "newest", "most-downloaded", "top-rated")
)
def test_package_list_view(client, community_site, ordering):
    for i in range(4):
        uploader = UploaderIdentityFactory.create(
            name=f"Tester_{i}",
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

    for i in range(2):
        uploader = UploaderIdentityFactory.create(
            name=f"RejectionTester_{i}",
        )
        package = PackageFactory.create(
            owner=uploader,
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
def test_package_detail_view(client, active_package, community_site):
    response = client.get(
        active_package.get_absolute_url(), HTTP_HOST=community_site.site.domain
    )
    assert response.status_code == 200
    response_text = response.content.decode("utf-8")
    assert active_package.name in response_text
    assert active_package.owner.name in response_text


@pytest.mark.django_db
def test_package_detail_version_view(client, active_version, community_site):
    response = client.get(
        active_version.get_absolute_url(), HTTP_HOST=community_site.site.domain
    )
    assert response.status_code == 200
    response_text = response.content.decode("utf-8")
    assert active_version.name in response_text
    assert active_version.owner.name in response_text


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
    identity = UploaderIdentity.get_or_create_for_user(user)
    file_data = {"file": SimpleUploadedFile("mod.zip", manifest_v1_package_bytes)}
    form = PackageUploadForm(
        user=user,
        files=file_data,
        community=community_site.community,
        data={
            "team": identity.name,
            "communities": [community_site.community.identifier],
        },
    )
    assert form.is_valid()
    version = form.save()
    assert version.package.owner == identity

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
def test_service_account_list_view(
    client, community_site, uploader_identity, uploader_identity_member
):
    client.force_login(uploader_identity_member.user)
    kwargs = {"name": uploader_identity.name}
    url = reverse("settings.teams.detail.service_accounts", kwargs=kwargs)
    response = client.get(url, HTTP_HOST=community_site.site.domain)
    assert response.status_code == 200
    assert f"Team {uploader_identity.name} service accounts" in str(response.content)


@pytest.mark.django_db
def test_service_account_creation(
    client, community_site, uploader_identity, uploader_identity_owner
):
    client.force_login(uploader_identity_owner.user)
    kwargs = {"name": uploader_identity.name}

    response = client.get(
        reverse("settings.teams.detail.add_service_account", kwargs=kwargs),
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 200
    assert b"Enter a nickname for the service account" in response.content

    response = client.post(
        reverse("settings.teams.detail.add_service_account", kwargs=kwargs),
        {"nickname": "Foo", "identity": uploader_identity.id},
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 200
    assert b'New service account <kbd class="text-info">Foo</kbd>' in response.content
    assert b'<pre class="important">tss_' in response.content
