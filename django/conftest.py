import io

import pytest
from django.contrib.sites.models import Site
from PIL import Image

from thunderstore.community.models import (
    Community,
    CommunitySite,
    PackageCategory,
    PackageListing,
)
from thunderstore.repository.consts import SPDX_LICENSE_IDS
from thunderstore.repository.factories import PackageFactory, PackageVersionFactory
from thunderstore.repository.models import Package, UploaderIdentity, Webhook
from thunderstore.webhooks.models import WebhookType


@pytest.fixture()
def user(django_user_model):
    return django_user_model.objects.create_user(
        username="Test",
        email="test@example.org",
        password="hunter2",
    )


@pytest.fixture()
def uploader_identity():
    return UploaderIdentity.objects.create(name="Test-Identity")


@pytest.fixture()
def package(uploader_identity):
    return Package.objects.create(
        owner=uploader_identity,
        name="Test_Package",
    )


@pytest.fixture()
def package_version(package):
    return PackageVersionFactory.create(
        package=package,
        name=package.name,
        version_number="1.0.0",
        website_url="https://example.org",
        description="Example mod",
        readme="# This is an example mod",
    )


@pytest.fixture()
def manifest_v1_data():
    return {
        "name": "name",
        "display_name": "display name",
        "author_name": "author_name",
        "version_number": "1.0.0",
        "license": next(iter(SPDX_LICENSE_IDS)),
        "website_url": "",
        "description": "",
        "dependencies": [],
    }


@pytest.fixture()
def icon_raw():
    icon_raw = io.BytesIO()
    icon = Image.new("RGB", (256, 256), "#FF0000")
    icon.save(icon_raw, format="PNG")
    return icon_raw


@pytest.fixture(scope="function")
def active_package():
    package = PackageFactory.create(
        is_active=True,
        is_deprecated=False,
    )
    PackageVersionFactory.create(
        name=package.name,
        package=package,
        is_active=True,
    )
    return package


@pytest.fixture(scope="function")
def active_package_listing(community, active_package):
    return PackageListing.objects.create(
        community=community,
        package=active_package,
    )


@pytest.fixture(scope="function")
def active_version(active_package):
    return active_package.versions.first()


@pytest.fixture()
def release_webhook(community_site):
    return Webhook.objects.create(
        name="test",
        webhook_url="https://example.com/",
        webhook_type=WebhookType.mod_release,
        is_active=True,
        community_site=community_site,
    )


@pytest.fixture()
def community():
    return Community.objects.create(name="Test", identifier="test")


@pytest.fixture()
def package_category(community):
    return PackageCategory.objects.create(
        name="Test",
        slug="test",
        community=community,
    )


@pytest.fixture()
def site():
    return Site.objects.create(domain="testsite.test", name="Testsite")


@pytest.fixture()
def community_site(community, site):
    return CommunitySite.objects.create(site=site, community=community)
