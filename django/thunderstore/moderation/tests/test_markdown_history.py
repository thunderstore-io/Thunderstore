from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.db import IntegrityError, connection, connections, transaction
from django.test.utils import CaptureQueriesContext

from thunderstore.api.cyberstorm.services.package_version import (
    update_markdown_override,
)
from thunderstore.api.cyberstorm.tests.utils import (
    delete_markdown,
    history_url,
    markdown_url,
    update_markdown,
)
from thunderstore.community.factories import CommunityFactory, PackageListingFactory
from thunderstore.community.models import CommunityMemberRole, CommunityMembership
from thunderstore.core.factories import UserFactory
from thunderstore.repository.factories import PackageVersionFactory, TeamMemberFactory
from thunderstore.repository.models import (
    PackageVersion,
    PackageVersionMarkdownRevision,
    TeamMemberRole,
)
from thunderstore.repository.validation.markdown import MAX_MARKDOWN_SIZE

pytestmark = pytest.mark.django_db


@pytest.fixture
def staff_client(api_client):
    api_client.force_authenticate(UserFactory(is_staff=True))
    return api_client


@pytest.mark.parametrize(
    "content",
    ["", "   ", "    indented code\n\n", "😀" * MAX_MARKDOWN_SIZE],
    ids=["empty", "whitespace", "indented-code", "unicode-limit"],
)
def test_content_round_trips_without_normalization(
    team_member_client, version, content
):
    response = update_markdown(
        team_member_client, version, "readme", {"content": content}
    )
    assert response.status_code == 200
    version.refresh_from_db()
    assert version.readme_override == content
    assert version.markdown_revisions.get().content == content
    assert (
        team_member_client.get(
            f"{markdown_url(version)}readme/download/"
        ).content.decode()
        == content
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"content": "x" * (MAX_MARKDOWN_SIZE + 1)},
        {"content": []},
        {"content": None},
        {},
    ],
)
def test_invalid_payload_writes_nothing(team_member_client, version, payload):
    response = update_markdown(team_member_client, version, "readme", payload)
    assert response.status_code == 400
    version.refresh_from_db()
    assert version.readme_override is None
    assert not version.markdown_revisions.exists()


def test_repeated_save_and_reset_do_not_amplify_history(team_member_client, version):
    assert delete_markdown(team_member_client, version, "readme").status_code == 204
    for _ in range(2):
        response = update_markdown(
            team_member_client, version, "readme", {"content": "changed"}
        )
        assert response.status_code == 200
    for _ in range(2):
        assert delete_markdown(team_member_client, version, "readme").status_code == 204
    assert list(version.markdown_revisions.values_list("content", "is_override")) == [
        (version.readme, False),
        ("changed", True),
    ]


def test_history_failure_rolls_back_the_write(team_member_client, version):
    with patch.object(
        PackageVersionMarkdownRevision.objects,
        "create",
        side_effect=IntegrityError("test history failure"),
    ):
        response = update_markdown(
            team_member_client, version, "readme", {"content": "new"}
        )
    assert response.status_code == 500
    version.refresh_from_db()
    assert version.readme_override is None
    assert not version.markdown_revisions.exists()


def test_reset_preserves_originals_and_records_missing_changelog(
    team_member_client, version
):
    update_markdown(team_member_client, version, "readme", {"content": "new"})
    update_markdown(team_member_client, version, "changelog", {"content": "new log"})
    delete_markdown(team_member_client, version, "readme")
    delete_markdown(team_member_client, version, "changelog")
    version.refresh_from_db()
    assert version.readme == "Original readme"
    assert version.changelog is None
    assert list(
        version.markdown_revisions.values_list("document", "content", "is_override")
    ) == [
        ("changelog", None, False),
        ("readme", "Original readme", False),
        ("changelog", "new log", True),
        ("readme", "new", True),
    ]


@pytest.mark.parametrize(
    "identity,expected",
    [
        ("anonymous", 401),
        ("owner", 403),
        ("stranger", 403),
        ("staff", 200),
        ("moderator", 200),
        ("other_moderator", 403),
        ("inactive_staff", 403),
    ],
)
def test_history_permissions(api_client, version, identity, expected):
    community = CommunityFactory()
    PackageListingFactory(package_=version.package, community_=community)
    if identity != "anonymous":
        user = UserFactory(
            is_staff=identity in ("staff", "inactive_staff"),
            is_active=identity != "inactive_staff",
        )
        if identity == "owner":
            TeamMemberFactory(
                user=user, team=version.package.owner, role=TeamMemberRole.owner
            )
        if identity in ("moderator", "other_moderator"):
            CommunityMembership.objects.create(
                user=user,
                community=community if identity == "moderator" else CommunityFactory(),
                role=CommunityMemberRole.moderator,
            )
        api_client.force_authenticate(user)
    response = api_client.get(history_url(version))
    assert response.status_code == expected
    assert "private" in response["Cache-Control"]
    assert "no-store" in response["Cache-Control"]


def test_inactive_version_history_remains_available_only_to_moderation(
    staff_client, version
):
    PackageVersion.objects.filter(pk=version.pk).update(is_active=False)
    assert staff_client.get(history_url(version)).status_code == 200
    assert (
        staff_client.get(f"{markdown_url(version)}readme/download/").status_code == 404
    )


def test_history_reads_are_bounded(staff_client, version):
    staff_client.get(history_url(version))
    with CaptureQueriesContext(connection) as empty:
        assert staff_client.get(history_url(version)).status_code == 200
    PackageVersionMarkdownRevision.objects.bulk_create(
        PackageVersionMarkdownRevision(
            version=version, document="readme", content=str(i), is_override=True
        )
        for i in range(25)
    )
    with CaptureQueriesContext(connection) as full:
        response = staff_client.get(history_url(version))
    assert len(response.json()["results"]) == 10
    assert len(full) == len(empty)
    history_queries = [
        q["sql"]
        for q in full
        if "repository_packageversionmarkdownrevision" in q["sql"]
    ]
    assert len(history_queries) == 1
    assert "LIMIT 11" in history_queries[0]
    assert "COUNT(" not in history_queries[0].upper()


@pytest.mark.parametrize(
    "document,content,is_override",
    [("invalid", "text", True), ("readme", None, False), ("changelog", None, True)],
)
def test_database_rejects_invalid_history(version, document, content, is_override):
    with pytest.raises(IntegrityError), transaction.atomic():
        version.markdown_revisions.create(
            document=document, content=content, is_override=is_override
        )


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("second_content", ["first", "second"])
def test_concurrent_saves_follow_lock_order(second_content):
    version = PackageVersionFactory(readme="original")
    user = UserFactory()
    TeamMemberFactory(user=user, team=version.package.owner, role=TeamMemberRole.owner)
    locking = Event()

    def observe_lock(execute, sql, params, many, context):
        if "FOR UPDATE" in sql:
            locking.set()
        return execute(sql, params, many, context)

    def save_second():
        try:
            with connection.execute_wrapper(observe_lock):
                update_markdown_override(user, version, "readme", second_content)
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=1) as executor:
        with transaction.atomic():
            PackageVersion.objects.select_for_update().get(pk=version.pk)
            pending = executor.submit(save_second)
            assert locking.wait(5)
            update_markdown_override(user, version, "readme", "first")
        pending.result(timeout=10)
    version.refresh_from_db()
    assert version.readme_override == second_content
    expected = ["second", "first"] if second_content == "second" else ["first"]
    assert (
        list(version.markdown_revisions.values_list("content", flat=True)) == expected
    )


def test_package_and_version_reads_stay_separate_across_new_upload(
    team_member_client, version
):
    listing = PackageListingFactory(package_=version.package)
    prefix = (
        f"/api/cyberstorm/package/{version.package.namespace}/{version.package.name}"
    )
    listing_url = f"/api/cyberstorm/listing/{listing.community.identifier}/{version.package.namespace}/{version.package.name}/"
    for document, content in (
        ("readme", "old version edit"),
        ("changelog", "old log edit"),
    ):
        response = update_markdown(
            team_member_client, version, document, {"content": content}
        )
        assert response.status_code == 200
    new = PackageVersionFactory(
        package=version.package,
        name=version.name,
        version_number="2.0.0",
        readme="new packaged readme",
        changelog=None,
    )
    # Edits don't bust the read endpoint caches.
    cache.clear()

    def html(path):
        return team_member_client.get(f"{prefix}/{path}").json()["html"]

    assert html("latest/readme/") == "<p>new packaged readme</p>\n"
    assert html(f"v/{version.version_number}/readme/") == "<p>old version edit</p>\n"
    assert html(f"v/{version.version_number}/changelog/") == "<p>old log edit</p>\n"
    assert team_member_client.get(f"{prefix}/latest/changelog/").status_code == 404
    assert team_member_client.get(listing_url).json()["has_changelog"] is False
    old_listing = team_member_client.get(f"{listing_url}v/{version.version_number}/")
    assert old_listing.json()["has_changelog"] is True

    response = update_markdown(
        team_member_client, new, "changelog", {"content": "new log edit"}
    )
    assert response.status_code == 200
    cache.clear()
    assert team_member_client.get(listing_url).json()["has_changelog"] is True

    assert delete_markdown(team_member_client, new, "changelog").status_code == 204
    cache.clear()
    assert team_member_client.get(listing_url).json()["has_changelog"] is False


def test_throttled_writes_do_not_create_history(team_member_client, version):
    for i in range(20):
        response = update_markdown(
            team_member_client, version, "readme", {"content": str(i)}
        )
        assert response.status_code == 200
    response = update_markdown(
        team_member_client, version, "readme", {"content": "blocked"}
    )
    assert response.status_code == 429
    version.refresh_from_db()
    assert version.readme_override == "19"
    assert version.markdown_revisions.count() == 20


def test_noop_does_not_change_attribution_or_other_document(
    team_member_client, version
):
    response = update_markdown(
        team_member_client, version, "readme", {"content": "saved"}
    )
    assert response.status_code == 200
    version.refresh_from_db()
    editor, timestamp = (
        version.readme_override_edited_by_id,
        version.readme_override_edited_at,
    )
    other_user = UserFactory()
    TeamMemberFactory(
        user=other_user, team=version.package.owner, role=TeamMemberRole.member
    )
    team_member_client.force_authenticate(other_user)
    for document, content in (("readme", "saved"), ("changelog", "new log")):
        response = update_markdown(
            team_member_client, version, document, {"content": content}
        )
        assert response.status_code == 200
    version.refresh_from_db()
    assert (
        version.readme_override_edited_by_id,
        version.readme_override_edited_at,
    ) == (editor, timestamp)
    assert version.changelog_override_edited_by_id == other_user.pk
    assert version.markdown_revisions.count() == 2


def test_history_documents_and_versions_do_not_leak(staff_client, version):
    other = PackageVersionFactory(
        package=version.package, name=version.name, version_number="2.0.0"
    )
    version.markdown_revisions.create(
        document="readme", content="target", is_override=True
    )
    version.markdown_revisions.create(
        document="changelog", content="other document", is_override=True
    )
    other.markdown_revisions.create(
        document="readme", content="other version", is_override=True
    )
    response = staff_client.get(history_url(version))
    assert [row["content"] for row in response.json()["results"]] == ["target"]
    assert response.json()["original"]["content"] == version.readme
    assert staff_client.get(history_url(version, "bogus")).status_code == 404
    assert staff_client.get(history_url(version) + "?cursor=invalid").status_code == 404
