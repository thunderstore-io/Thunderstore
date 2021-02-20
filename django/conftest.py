from copy import copy

import pytest
from django.contrib.auth.models import AnonymousUser
from django.contrib.sites.models import Site
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from thunderstore.account.forms import CreateServiceAccountForm, CreateTokenForm
from thunderstore.account.models import ServiceAccount
from thunderstore.community.models import (
    Community,
    CommunitySite,
    PackageCategory,
    PackageListing,
)
from thunderstore.core.utils import ChoiceEnum
from thunderstore.repository.factories import (
    PackageFactory,
    PackageVersionFactory,
    ThunderstoreUserFactory,
    UploaderIdentityFactory,
    UploaderIdentityMemberFactory,
)
from thunderstore.repository.models import (
    Package,
    UploaderIdentity,
    UploaderIdentityMember,
    UploaderIdentityMemberRole,
    Webhook,
)
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
    return UploaderIdentity.objects.create(name="Test_Identity")


@pytest.fixture()
def uploader_identity_member(uploader_identity):
    return UploaderIdentityMember.objects.create(
        identity=uploader_identity,
        user=ThunderstoreUserFactory(),
        role=UploaderIdentityMemberRole.member,
    )


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
        "version_number": "1.0.0",
        "website_url": "",
        "description": "",
        "dependencies": [],
    }


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


@pytest.fixture()
def celery_app():
    from celery import Celery, _state

    app = Celery("thunderstore", set_as_current=False)
    app.config_from_object("django.conf:settings", namespace="CELERY")
    app.autodiscover_tasks(force=True)
    on_app_finalizers = copy(_state._on_app_finalizers)
    yield app
    _state._deregister_app(app)
    # Registering a new task creates a hook that adds it to all future app
    # instances, meaning that we need to restore the hooks to pre-test
    # state as to not spill over tasks to other tests
    _state._on_app_finalizers = on_app_finalizers


@pytest.fixture(autouse=True)
def _use_static_files_storage(settings):
    settings.STATICFILES_STORAGE = (
        "django.contrib.staticfiles.storage.StaticFilesStorage"
    )


@pytest.fixture()
def service_account(user, uploader_identity) -> ServiceAccount:
    UploaderIdentityMember.objects.create(
        user=user,
        identity=uploader_identity,
        role=UploaderIdentityMemberRole.owner,
    )
    form = CreateServiceAccountForm(
        user,
        data={"identity": uploader_identity, "nickname": "Nickname"},
    )
    assert form.is_valid()
    return form.save()


@pytest.fixture()
def service_account_token(service_account) -> Token:
    member = service_account.owner.members.first()
    assert member.role == UploaderIdentityMemberRole.owner
    form = CreateTokenForm(
        member.user,
        data={"service_account": service_account},
    )
    assert form.is_valid()
    return form.save()


@pytest.fixture()
def api_client(community_site) -> APIClient:
    return APIClient(HTTP_HOST=community_site.site.domain)


def create_test_service_account_user():
    identity_owner = ThunderstoreUserFactory()
    identity = UploaderIdentityFactory()
    UploaderIdentityMemberFactory(user=identity_owner, identity=identity, role="owner")
    form = CreateServiceAccountForm(
        user=identity_owner,
        data={"identity": identity, "nickname": "Nickname"},
    )
    assert form.is_valid()
    return form.save().user


class TestUserTypes(ChoiceEnum):
    no_user = "none"
    unauthenticated = "unauthenticated"
    regular_user = "regular_user"
    deactivated_user = "deactivated_user"
    service_account = "service_account"
    superuser = "superuser"

    @classmethod
    def real_users(cls):
        """ Returns only actual database-level user objects """
        return (
            cls.regular_user,
            cls.service_account,
            cls.superuser,
        )

    @classmethod
    def fake_users(cls):
        return (cls.no_user, cls.unauthenticated)

    @staticmethod
    def get_user_by_type(usertype: str):
        if usertype == TestUserTypes.no_user:
            return None
        if usertype == TestUserTypes.unauthenticated:
            return AnonymousUser()
        if usertype == TestUserTypes.regular_user:
            return ThunderstoreUserFactory.create()
        if usertype == TestUserTypes.deactivated_user:
            return ThunderstoreUserFactory.create(is_active=False)
        if usertype == TestUserTypes.service_account:
            return create_test_service_account_user()
        if usertype == TestUserTypes.superuser:
            return ThunderstoreUserFactory.create(is_staff=True, is_superuser=True)
        raise AttributeError(f"Invalid useretype: {usertype}")
