"""Check moderation polling, access boundaries, and concurrent commits."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from django.contrib.auth.models import Permission
from django.db import connection, connections, transaction
from django.test.utils import CaptureQueriesContext

from thunderstore.api.cyberstorm.services.package_version import (
    update_markdown_overrides,
)
from thunderstore.api.cyberstorm.tests.utils import (
    get_resolver,
    get_schema,
    history_url,
    validate_response_against_schema,
)
from thunderstore.community.factories import CommunityFactory, PackageListingFactory
from thunderstore.community.models import CommunityMembership
from thunderstore.core.factories import UserFactory
from thunderstore.repository.factories import PackageVersionFactory, TeamMemberFactory
from thunderstore.repository.models import PackageVersionMarkdownRevision

pytestmark = pytest.mark.django_db
URL = "/moderation/api/markdown/changes/"


@pytest.fixture
def moderator():
    user = UserFactory()
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="repository",
            codename="view_packageversionmarkdownrevision",
        )
    )
    return user


@pytest.fixture
def moderator_client(api_client, moderator):
    api_client.force_authenticate(moderator)
    return api_client


@pytest.fixture
def author_version():
    version = PackageVersionFactory()
    member = TeamMemberFactory(team=version.package.owner, role="owner")
    return member.user, version


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        ("anonymous", 401),
        ("author", 403),
        ("staff", 403),
        ("superuser", 200),
        ("security", 200),
    ],
)
def test_feed_permissions(role, expected, moderator, author_version, api_client):
    author, _ = author_version
    if role in ("staff", "superuser"):
        user = UserFactory(is_staff=role == "staff", is_superuser=role == "superuser")
    else:
        user = {"anonymous": None, "author": author, "security": moderator}[role]
    api_client.force_authenticate(user)
    response = api_client.get(URL)
    assert response.status_code == expected
    assert "private" in response["Cache-Control"]
    assert "no-store" in response["Cache-Control"]


def test_polling_includes_resets_and_inactive_versions(
    moderator_client, author_version
):
    author, version = author_version
    for i in range(12):
        update_markdown_overrides(author, version, {"readme": str(i)})
    update_markdown_overrides(author, version, {"changelog": "log"})
    update_markdown_overrides(author, version, {"changelog": None})
    version.package.is_active = False
    version.package.save(update_fields=["is_active"])
    version.is_active = False
    version.save(update_fields=["is_active"])

    first = moderator_client.get(URL).json()
    assert len(first["results"]) == 10
    assert first["has_more"] is True
    second = moderator_client.get(URL, {"after": first["cursor"]}).json()
    assert second["has_more"] is False
    results = first["results"] + second["results"]
    assert [row["id"] for row in results] == list(
        version.markdown_revisions.order_by("id").values_list("id", flat=True)
    )
    assert results[-1]["document"] == "changelog"
    assert results[-1]["is_override"] is False
    assert results[-1]["content"] == version.changelog
    assert results[0]["edited_by"] == author.pk
    assert results[0]["editor_username"] == author.username
    assert results[0]["version_id"] == version.pk
    assert results[0]["namespace"] == version.package.namespace.name
    assert results[0]["package_name"] == version.package.name
    assert results[0]["version_number"] == version.version_number

    empty = moderator_client.get(URL, {"after": second["cursor"]}).json()
    assert empty == {"results": [], "cursor": second["cursor"], "has_more": False}
    update_markdown_overrides(author, version, {"readme": "next"})
    resumed = moderator_client.get(URL, {"after": empty["cursor"]}).json()
    assert [row["content"] for row in resumed["results"]] == ["next"]
    assert moderator_client.get(history_url(version)).status_code == 200


@pytest.mark.parametrize("after", ["bad", "-1", str(2**63)])
def test_invalid_cursor(moderator_client, after):
    response = moderator_client.get(URL, {"after": after})
    assert response.status_code == 400
    assert "no-store" in response["Cache-Control"]


def test_community_moderator_cannot_read_global_feed(api_client, author_version):
    author, version = author_version
    community = CommunityFactory()
    PackageListingFactory(package_=version.package, community_=community)
    CommunityMembership.objects.create(
        user=author, community=community, role="moderator"
    )
    api_client.force_authenticate(author)
    assert api_client.get(history_url(version)).status_code == 200
    assert api_client.get(URL).status_code == 403


def test_inactive_moderator_is_denied(moderator_client, moderator, author_version):
    _, version = author_version
    moderator.is_active = False
    moderator.save(update_fields=["is_active"])
    assert moderator_client.get(URL).status_code == 403
    assert moderator_client.get(history_url(version)).status_code == 403


def test_feed_response_schema_with_deleted_author(moderator_client, author_version):
    author, version = author_version
    update_markdown_overrides(author, version, {"readme": "edit"})
    author.delete()
    response = moderator_client.get(URL)
    row = response.json()["results"][0]
    assert row["edited_by"] is None
    assert row["editor_username"] is None
    schema = get_schema(moderator_client)
    assert (
        validate_response_against_schema(
            response, URL, "get", schema, get_resolver(schema)
        )
        == []
    )


def test_feed_uses_a_bounded_query(moderator_client, author_version):
    author, version = author_version
    PackageVersionMarkdownRevision.objects.bulk_create(
        [
            PackageVersionMarkdownRevision(
                version=version,
                document="readme",
                content=str(i),
                is_override=True,
                edited_by=author,
            )
            for i in range(3000)
        ]
    )
    ids = list(version.markdown_revisions.order_by("id").values_list("id", flat=True))
    moderator_client.get(URL, {"after": ids[-1]})
    with CaptureQueriesContext(connection) as empty:
        moderator_client.get(URL, {"after": ids[-1]})
    with CaptureQueriesContext(connection) as queries:
        response = moderator_client.get(URL, {"after": ids[2980]})
    assert response.status_code == 200
    assert len(response.json()["results"]) == 10
    assert len(queries) == len(empty)
    feed_queries = [
        q["sql"]
        for q in queries
        if "repository_packageversionmarkdownrevision" in q["sql"]
    ]
    assert len(feed_queries) == 1
    sql = feed_queries[0]
    assert "LIMIT 11" in sql
    assert "COUNT(" not in sql
    assert "OFFSET" not in sql
    assert '"readme"' not in sql


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("rollback", [False, True])
def test_polling_does_not_skip_a_late_commit(
    moderator_client, author_version, rollback
):
    author, first = author_version
    second = PackageVersionFactory()
    TeamMemberFactory(team=second.package.owner, user=author, role="owner")
    inserted = Event()
    release = Event()
    waiting = Event()

    def save_first():
        try:
            with transaction.atomic():
                update_markdown_overrides(author, first, {"readme": "first"})
                inserted.set()
                assert release.wait(10)
                if rollback:
                    transaction.set_rollback(True)
        finally:
            connections.close_all()

    def observe_lock(execute, sql, params, many, context):
        if "pg_advisory_xact_lock" in sql:
            waiting.set()
        return execute(sql, params, many, context)

    def save_second():
        try:
            with connection.execute_wrapper(observe_lock):
                update_markdown_overrides(author, second, {"readme": "second"})
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_save = executor.submit(save_first)
        try:
            assert inserted.wait(10)
            second_save = executor.submit(save_second)
            assert waiting.wait(10)
            page = moderator_client.get(URL).json()
            assert page == {"results": [], "cursor": 0, "has_more": False}
        finally:
            release.set()
        first_save.result(timeout=10)
        second_save.result(timeout=10)

    page = moderator_client.get(URL, {"after": page["cursor"]}).json()
    expected = ["second"] if rollback else ["first", "second"]
    assert [row["content"] for row in page["results"]] == expected
