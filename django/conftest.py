import io
import json
import threading
from copy import copy, deepcopy
from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer as SuperHTTPServer
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from django.contrib.auth.models import AnonymousUser, Permission
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.files.base import File
from PIL import Image
from rest_framework.test import APIClient

from django_contracts.models import LegalContract, LegalContractVersion
from thunderstore.account.factories import UserFlagFactory
from thunderstore.account.forms import CreateServiceAccountForm
from thunderstore.account.models import ServiceAccount, UserFlag, UserSettings
from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.models import (
    Community,
    CommunityAggregatedFields,
    CommunitySite,
    PackageCategory,
    PackageListing,
    PackageListingSection,
)
from thunderstore.core.factories import UserFactory
from thunderstore.core.types import UserType
from thunderstore.core.utils import ChoiceEnum
from thunderstore.repository.factories import (
    AsyncPackageSubmissionFactory,
    NamespaceFactory,
    PackageFactory,
    PackageVersionFactory,
    PackageWikiFactory,
    TeamFactory,
    TeamMemberFactory,
)
from thunderstore.repository.models import (
    AsyncPackageSubmission,
    Package,
    PackageVersion,
    PackageWiki,
    Team,
    TeamMember,
    TeamMemberRole,
    Webhook,
)
from thunderstore.repository.models.namespace import Namespace
from thunderstore.schema_server.factories import SchemaChannelFactory
from thunderstore.usermedia.tests.utils import create_and_upload_usermedia
from thunderstore.webhooks.models.release import WebhookType
from thunderstore.wiki.factories import WikiFactory, WikiPageFactory
from thunderstore.wiki.models import Wiki, WikiPage


class HTTPServer(SuperHTTPServer):
    """
    Class for wrapper to run SimpleHTTPServer on Thread.
    Ctrl +Only Thread remains dead when terminated with C.
    Keyboard Interrupt passes.
    """

    def run(self):
        try:
            self.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.server_close()


class PostHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        self.send_response(200)
        self.end_headers()
        return


@pytest.fixture()
def http_server():
    host, port = "localhost", 8888
    url = f"http://{host}:{port}/"
    server = HTTPServer((host, port), PostHTTPRequestHandler)
    thread = threading.Thread(None, server.run)
    thread.start()
    yield url
    server.shutdown()
    thread.join()


@pytest.mark.django_db
@pytest.fixture(scope="session", autouse=True)
def prime_testing_database(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        [x.delete() for x in PackageVersion.objects.all()]
        [x.delete() for x in Package.objects.all()]
        [x.delete() for x in PackageListing.objects.all()]
        [x.delete() for x in PackageCategory.objects.all()]
        [x.delete() for x in Webhook.objects.all()]
        [x.delete() for x in CommunitySite.objects.all()]
        [x.delete() for x in Community.objects.all()]
        [x.delete() for x in CommunityAggregatedFields.objects.all()]
        [x.delete() for x in Site.objects.all()]


@pytest.fixture()
def user(django_user_model):
    return django_user_model.objects.create_user(
        username="Test",
        email="test@example.org",
        password="hunter2",
    )


@pytest.fixture()
def user_with_settings(django_user_model):
    user = django_user_model.objects.create_user(
        username="SettingsTest",
        email="test@example.org",
        password="hunter2",
    )
    UserSettings.get_for_user(user)
    return user


@pytest.fixture()
def team():
    return Team.create(name="Test_Team")


@pytest.fixture()
def team_member(team):
    return TeamMember.objects.create(
        team=team,
        user=UserFactory(),
        role=TeamMemberRole.member,
    )


@pytest.fixture()
def team_owner(team):
    return TeamMember.objects.create(
        team=team,
        user=UserFactory(),
        role=TeamMemberRole.owner,
    )


@pytest.fixture()
def published_legal_contract() -> LegalContract:
    contract = LegalContract.objects.create(
        slug="test-contract",
        title="Test Contract",
    )
    contract.publish()
    return contract


@pytest.fixture()
def published_legal_contract_version(
    published_legal_contract: LegalContract,
) -> LegalContractVersion:
    version = LegalContractVersion.objects.create(
        contract=published_legal_contract,
        html_content="<h2>Test contract</h2>",
        markdown_content="## Test Contract",
    )
    version.publish()
    return version


@pytest.fixture()
def namespace(team) -> Namespace:
    return NamespaceFactory.create(team=team)


@pytest.fixture()
def package(team, namespace) -> Package:
    return Package.objects.create(owner=team, name="Test_Package", namespace=namespace)


@pytest.fixture()
def package_version(package):
    return PackageVersionFactory.create(
        package=package,
        name=package.name,
        version_number="1.0.0",
        website_url="https://example.org",
        description="Example mod",
        readme="# This is an example mod",
        changelog="# This is an example changelog",
    )


@pytest.fixture(scope="function")
def manifest_v1_data():
    return {
        "name": "name",
        "version_number": "1.0.0",
        "website_url": "",
        "description": "",
        "dependencies": [],
    }


@pytest.fixture(scope="function")
def active_package(team) -> Package:
    namespace = team.get_namespace()
    package = PackageFactory.create(
        is_active=True, is_deprecated=False, owner=team, namespace=namespace
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
def rejected_package_listing(community, active_package):
    return PackageListing.objects.create(
        community=community,
        package=active_package,
        review_status=PackageListingReviewStatus.rejected,
    )


@pytest.fixture(scope="function")
def active_version(active_package):
    return active_package.versions.first()


@pytest.fixture(scope="function")
def active_version_with_listing(active_package_listing):
    return active_package_listing.package.versions.first()


@pytest.fixture()
def release_webhook(community):
    return Webhook.objects.create(
        name="test",
        webhook_url="https://example.com/",
        webhook_type=WebhookType.mod_release,
        is_active=True,
        community=community,
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
def package_listing_section(community):
    return PackageListingSection.objects.create(
        community=community,
        name="Test Section",
        slug="test-section",
        is_listed=True,
    )


@pytest.fixture()
def schema_channel():
    return SchemaChannelFactory()


@pytest.fixture()
def site():
    return Site.objects.create(domain="testsite.test", name="Testsite")


@pytest.fixture(autouse=True, scope="session")
def setup_cache(request):
    """
    This fixture will ensure each (even if parallel) test runner will use a
    different redis database (hopefully).

    It's assumed that redis is in use and that the max worker ID doesn't go over
    14, as 15 is the default amount of redis databases.
    """
    from django.conf import settings
    from django.core.cache import DEFAULT_CACHE_ALIAS, _create_cache, caches

    xdist_suffix = getattr(request.config, "workerinput", {}).get("workerid")
    if xdist_suffix:
        db_id = int("".join(x for x in xdist_suffix if x.isdigit())) + 1
    else:
        db_id = 1
    assert (
        settings.CACHES[DEFAULT_CACHE_ALIAS]["BACKEND"]
        == "django_redis.cache.RedisCache"
    )
    new_caches = deepcopy(settings.CACHES)
    parts = new_caches[DEFAULT_CACHE_ALIAS]["LOCATION"].split("/")
    assert parts[-1] == "0"
    parts[-1] = str(db_id)
    new_caches[DEFAULT_CACHE_ALIAS]["LOCATION"] = "/".join(parts)
    settings.CACHES = new_caches
    caches._caches.caches[DEFAULT_CACHE_ALIAS] = _create_cache(DEFAULT_CACHE_ALIAS)


@pytest.fixture(scope="session")
def django_db_setup(setup_cache, django_db_setup):
    # We have to override this as to set up the test cache before db calls are
    # made, as django-cachalot uses the cache already during setup.
    pass


@pytest.fixture(scope="function", autouse=True)
def autoclear_cache(settings, worker_id) -> None:
    # The cache_id assertion is just a sanity check to ensure we don't have
    # cache conflicts when the test run is parallelized across multiple workers
    cache_id = settings.CACHES["default"]["LOCATION"].split("/")[-1]
    worker_num = int("".join(x for x in worker_id if x.isdigit()) or "0") + 1
    assert cache_id == str(worker_num)
    cache.clear()


@pytest.fixture()
def community_site(community, site):
    return CommunitySite.objects.create(site=site, community=community)


@pytest.fixture()
def wiki() -> Wiki:
    return WikiFactory()


@pytest.fixture()
def wiki_page(wiki: Wiki) -> WikiPage:
    return WikiPageFactory(wiki=wiki)


@pytest.fixture()
def package_wiki(wiki: Wiki, package: Package) -> PackageWiki:
    return PackageWikiFactory(wiki=wiki, package=package)


@pytest.fixture()
def active_package_wiki(wiki: Wiki, active_package: Package) -> PackageWiki:
    return PackageWikiFactory(wiki=wiki, package=active_package)


@pytest.fixture()
def package_wiki_page(package_wiki: PackageWiki) -> WikiPage:
    return WikiPageFactory(wiki=package_wiki.wiki)


@pytest.fixture()
def active_package_wiki_page(active_package_wiki: PackageWiki) -> WikiPage:
    return WikiPageFactory(wiki=active_package_wiki.wiki)


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
def service_account(user, team) -> ServiceAccount:
    TeamMember.objects.create(
        user=user,
        team=team,
        role=TeamMemberRole.owner,
    )
    form = CreateServiceAccountForm(
        user,
        data={"team": team, "nickname": "Nickname"},
    )
    assert form.is_valid()
    return form.save()


@pytest.fixture()
def user_flag() -> UserFlag:
    return UserFlagFactory()


@pytest.fixture()
def api_client(community_site) -> APIClient:
    return APIClient(HTTP_HOST=community_site.site.domain)


@pytest.fixture(scope="session")
def manifest_v1_package_bytes() -> bytes:
    icon_raw = io.BytesIO()
    icon = Image.new("RGB", (256, 256), "#FF0000")
    icon.save(icon_raw, format="PNG")

    readme = "# Test readme".encode("utf-8")
    manifest = json.dumps(
        {
            "name": "name",
            "version_number": "1.0.0",
            "website_url": "",
            "description": "",
            "dependencies": [],
        }
    ).encode("utf-8")

    files = [
        ("README.md", readme),
        ("icon.png", icon_raw.getvalue()),
        ("manifest.json", manifest),
    ]

    zip_raw = io.BytesIO()
    with ZipFile(zip_raw, "a", ZIP_DEFLATED, False) as zip_file:
        for name, data in files:
            zip_file.writestr(name, data)

    return zip_raw.getvalue()


@pytest.fixture(scope="function")
def dummy_image() -> Image:
    file_obj = io.BytesIO()
    image = Image.new("RGB", (1, 1), "#C0FFEE")
    image.save(file_obj, format="PNG")
    file_obj.seek(0)
    return File(file_obj, name="test.png")


@pytest.fixture(scope="function")
def manifest_v1_package_upload_id(
    manifest_v1_package_bytes: bytes,
    api_client: APIClient,
    user: UserType,
    settings: Any,
) -> str:
    checks_disabled = settings.DISABLE_TRANSACTION_CHECKS
    settings.DISABLE_TRANSACTION_CHECKS = True
    upload_id = create_and_upload_usermedia(
        api_client=api_client,
        user=user,
        settings=settings,
        upload=manifest_v1_package_bytes,
    )
    settings.DISABLE_TRANSACTION_CHECKS = checks_disabled
    return upload_id


@pytest.fixture(scope="function")
def async_package_submission(
    user: UserType,
    team: Team,
    community: Community,
    manifest_v1_package_upload_id: str,
) -> AsyncPackageSubmission:
    return AsyncPackageSubmissionFactory(
        owner=user,
        file_id=manifest_v1_package_upload_id,
        form_data={
            "team": team.name,
            "communities": [community.identifier],
        },
    )


def create_test_service_account_user():
    team_owner = UserFactory()
    team = TeamFactory()
    TeamMemberFactory(user=team_owner, team=team, role="owner")
    form = CreateServiceAccountForm(
        user=team_owner,
        data={"team": team, "nickname": "Nickname"},
    )
    assert form.is_valid()
    return form.save().user


class TestUserTypes(ChoiceEnum):
    no_user = "none"
    unauthenticated = "unauthenticated"
    regular_user = "regular_user"
    deactivated_user = "deactivated_user"
    service_account = "service_account"
    site_admin = "site_admin"
    superuser = "superuser"

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
            return UserFactory.create()
        if usertype == TestUserTypes.deactivated_user:
            return UserFactory.create(is_active=False)
        if usertype == TestUserTypes.service_account:
            return create_test_service_account_user()
        if usertype == TestUserTypes.site_admin:
            user = UserFactory.create(is_staff=True)
            perm = Permission.objects.get(
                content_type__app_label="repository",
                codename="change_package",
            )
            user.user_permissions.add(perm)
            return user
        if usertype == TestUserTypes.superuser:
            return UserFactory.create(is_staff=True, is_superuser=True)
        raise AttributeError(f"Invalid useretype: {usertype}")
