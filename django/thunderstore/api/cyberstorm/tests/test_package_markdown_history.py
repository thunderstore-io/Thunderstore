"""Exercise markdown history integrity, access control, and bounded reads."""

import importlib
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch

import pytest
from django.apps import apps
from django.core.cache import cache
from django.db import IntegrityError, connection, connections, transaction
from django.test.utils import CaptureQueriesContext

from thunderstore.api.cyberstorm.services.package_version import (
    update_markdown_overrides,
)
from thunderstore.api.cyberstorm.tests.test_package_version_markdown import (
    markdown_url,
    post_markdown,
    team_member_client,
    version,
)
from thunderstore.community.factories import CommunityFactory, PackageListingFactory
from thunderstore.community.models import CommunityMembership
from thunderstore.core.factories import UserFactory
from thunderstore.repository.factories import PackageVersionFactory, TeamMemberFactory
from thunderstore.repository.models import (
    PackageVersion,
    PackageVersionMarkdownRevision,
)
from thunderstore.repository.validation.markdown import MAX_MARKDOWN_SIZE

pytestmark = pytest.mark.django_db


def history_url(version, document="readme"):
    return f"{markdown_url(version)}{document}/history/"


@pytest.fixture
def admin_client(api_client):
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
    response = post_markdown(team_member_client, version, {"readme": content})
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
        {"readme": "x" * (MAX_MARKDOWN_SIZE + 1)},
        {"readme": []},
        {"readme": {}, "changelog": "valid"},
    ],
)
def test_invalid_payload_writes_nothing(team_member_client, version, payload):
    assert post_markdown(team_member_client, version, payload).status_code == 400
    version.refresh_from_db()
    assert version.readme_override is None
    assert version.changelog_override is None
    assert not version.markdown_revisions.exists()


def test_empty_request_writes_no_history(team_member_client, version):
    assert post_markdown(team_member_client, version, {}).status_code == 200
    assert not version.markdown_revisions.exists()


def test_repeated_save_and_reset_do_not_amplify_history(team_member_client, version):
    for payload in [
        {"readme": None},
        {"readme": "changed"},
        {"readme": "changed"},
        {"readme": None},
        {"readme": None},
    ]:
        assert post_markdown(team_member_client, version, payload).status_code == 200
    assert list(version.markdown_revisions.values_list("content", "is_override")) == [
        (version.readme, False),
        ("changed", True),
    ]


def test_history_failure_rolls_back_both_documents(team_member_client, version):
    with patch.object(
        PackageVersionMarkdownRevision.objects,
        "bulk_create",
        side_effect=IntegrityError("test history failure"),
    ):
        response = post_markdown(
            team_member_client, version, {"readme": "new", "changelog": "new log"}
        )
    assert response.status_code == 500
    version.refresh_from_db()
    assert version.readme_override is None
    assert version.changelog_override is None
    assert not version.markdown_revisions.exists()


def test_stale_version_rejects_whole_mixed_update(team_member_client, version):
    PackageVersionFactory(
        package=version.package, name=version.name, version_number="2.0.0"
    )
    assert (
        post_markdown(
            team_member_client, version, {"readme": "new", "changelog": "new log"}
        ).status_code
        == 400
    )
    version.refresh_from_db()
    assert version.readme_override is None
    assert not version.markdown_revisions.exists()


def test_reset_preserves_originals_and_records_missing_changelog(
    team_member_client, version
):
    post_markdown(
        team_member_client, version, {"readme": "new", "changelog": "new log"}
    )
    post_markdown(team_member_client, version, {"readme": None, "changelog": None})
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
            TeamMemberFactory(user=user, team=version.package.owner, role="owner")
        if identity in ("moderator", "other_moderator"):
            CommunityMembership.objects.create(
                user=user,
                community=community if identity == "moderator" else CommunityFactory(),
                role="moderator",
            )
        api_client.force_authenticate(user)
    response = api_client.get(history_url(version))
    assert response.status_code == expected
    assert "private" in response["Cache-Control"]
    assert "no-store" in response["Cache-Control"]


def test_inactive_version_history_remains_available_only_to_moderation(
    admin_client, version
):
    PackageVersion.objects.filter(pk=version.pk).update(is_active=False)
    assert admin_client.get(history_url(version)).status_code == 200
    assert (
        admin_client.get(f"{markdown_url(version)}readme/download/").status_code == 404
    )


def test_history_pagination_survives_new_saves(admin_client, version):
    rows = PackageVersionMarkdownRevision.objects.bulk_create(
        [
            PackageVersionMarkdownRevision(
                version=version, document="readme", content=str(i), is_override=True
            )
            for i in range(35)
        ]
    )
    response = admin_client.get(history_url(version))
    assert response.status_code == 200
    assert response.json()["original"]["content"] == version.readme
    seen = [row["id"] for row in response.json()["results"]]
    version.markdown_revisions.create(
        document="readme", content="new arrival", is_override=True
    )
    while response.json()["next"]:
        response = admin_client.get(response.json()["next"])
        seen.extend(row["id"] for row in response.json()["results"])
    assert seen == [row.pk for row in reversed(rows)]
    assert len(seen) == len(set(seen))


def test_large_history_reads_are_bounded_and_indexed(admin_client, version):
    admin_client.get(history_url(version))
    with CaptureQueriesContext(connection) as small:
        assert admin_client.get(history_url(version)).status_code == 200
    PackageVersionMarkdownRevision.objects.bulk_create(
        [
            PackageVersionMarkdownRevision(
                version=version,
                document="readme",
                content=f"{i}:" + "x" * 4096,
                is_override=True,
            )
            for i in range(3000)
        ],
        batch_size=100,
    )
    other = PackageVersionFactory()
    PackageVersionMarkdownRevision.objects.bulk_create(
        [
            PackageVersionMarkdownRevision(
                version=other,
                document="readme",
                content=f"Unrelated revision {i}",
                is_override=True,
            )
            for i in range(3000)
        ],
        batch_size=100,
    )
    with connection.cursor() as cursor:
        cursor.execute("ANALYZE repository_packageversionmarkdownrevision")
    with CaptureQueriesContext(connection) as large:
        response = admin_client.get(history_url(version))
    assert response.status_code == 200
    assert len(response.json()["results"]) == 10
    assert len(large) == len(small)
    history_queries = [
        q["sql"]
        for q in large
        if "repository_packageversionmarkdownrevision" in q["sql"]
    ]
    assert len(history_queries) == 1
    assert "LIMIT 11" in history_queries[0]
    assert "COUNT(" not in history_queries[0].upper()
    plan = version.markdown_revisions.filter(document="readme")[:11].explain(
        analyze=True, buffers=True
    )
    assert "Index Scan" in plan
    assert "Sort" not in plan
    print(f"\nHistory query count: {len(large)} for both 0 and 3000 revisions\n{plan}")


@pytest.mark.parametrize(
    "document,content,is_override",
    [("invalid", "text", True), ("readme", None, False), ("changelog", None, True)],
)
def test_database_rejects_invalid_history(version, document, content, is_override):
    with pytest.raises(IntegrityError), transaction.atomic():
        version.markdown_revisions.create(
            document=document, content=content, is_override=is_override
        )


def test_deleting_author_preserves_history_and_deleting_version_cascades(version):
    author = UserFactory()
    row = version.markdown_revisions.create(
        document="readme", content="audit", is_override=True, edited_by=author
    )
    author.delete()
    row.refresh_from_db()
    assert row.edited_by_id is None
    assert row.content == "audit"
    version.delete()
    assert not PackageVersionMarkdownRevision.objects.filter(pk=row.pk).exists()


def test_backfill_is_idempotent_and_preserves_existing_history(version):
    PackageVersion.objects.filter(pk=version.pk).update(
        readme_override="", changelog_override="old log"
    )
    revision = version.markdown_revisions.create(
        document="changelog", content="existing history", is_override=True
    )
    migration = importlib.import_module(
        "thunderstore.repository.migrations.0069_preserve_markdown_overrides"
    )
    with connection.schema_editor(atomic=False) as editor:
        migration.preserve_existing_overrides(apps, editor)
        migration.preserve_existing_overrides(apps, editor)
    assert version.markdown_revisions.count() == 2
    assert version.markdown_revisions.get(document="readme").content == ""
    assert version.markdown_revisions.get(document="changelog").pk == revision.pk


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("second_content", ["first", "second"])
def test_concurrent_saves_follow_lock_order(second_content):
    version = PackageVersionFactory(readme="original")
    user = UserFactory()
    TeamMemberFactory(user=user, team=version.package.owner, role="owner")
    started = Event()

    def save_second():
        try:
            started.set()
            update_markdown_overrides(user, version, {"readme": second_content})
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=1) as executor:
        with transaction.atomic():
            PackageVersion.objects.select_for_update().get(pk=version.pk)
            pending = executor.submit(save_second)
            assert started.wait(5)
            update_markdown_overrides(user, version, {"readme": "first"})
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
    assert (
        post_markdown(
            team_member_client,
            version,
            {"readme": "old version edit", "changelog": "old log edit"},
        ).status_code
        == 200
    )
    new = PackageVersionFactory(
        package=version.package,
        name=version.name,
        version_number="2.0.0",
        readme="new packaged readme",
        changelog=None,
    )
    # Public endpoints intentionally retain their cache until expiry.
    cache.clear()
    assert (
        team_member_client.get(f"{prefix}/latest/readme/").json()["html"]
        == "<p>new packaged readme</p>\n"
    )
    assert (
        team_member_client.get(f"{prefix}/v/{version.version_number}/readme/").json()[
            "html"
        ]
        == "<p>old version edit</p>\n"
    )
    assert team_member_client.get(listing_url).json()["has_changelog"] is False
    assert (
        team_member_client.get(f"{listing_url}v/{version.version_number}/").json()[
            "has_changelog"
        ]
        is True
    )
    assert (
        post_markdown(team_member_client, version, {"changelog": None}).status_code
        == 400
    )
    assert (
        post_markdown(
            team_member_client, version, {"readme": "revised old readme"}
        ).status_code
        == 200
    )
    assert (
        post_markdown(
            team_member_client, new, {"changelog": "new log edit"}
        ).status_code
        == 200
    )
    cache.clear()
    assert team_member_client.get(listing_url).json()["has_changelog"] is True
    assert (
        team_member_client.get(f"{prefix}/latest/changelog/").json()["html"]
        == "<p>new log edit</p>\n"
    )
    assert (
        team_member_client.get(
            f"{prefix}/v/{version.version_number}/changelog/"
        ).json()["html"]
        == "<p>old log edit</p>\n"
    )
    assert (
        post_markdown(team_member_client, new, {"changelog": None}).status_code == 200
    )
    cache.clear()
    assert team_member_client.get(listing_url).json()["has_changelog"] is False
    assert team_member_client.get(f"{prefix}/latest/changelog/").status_code == 404
    assert (
        team_member_client.get(
            f"{prefix}/v/{version.version_number}/changelog/"
        ).status_code
        == 200
    )
    assert set(version.markdown_revisions.values_list("content", flat=True)) == {
        "old version edit",
        "old log edit",
        "revised old readme",
    }
    assert set(new.markdown_revisions.values_list("content", flat=True)) == {
        "new log edit",
        None,
    }


def test_throttled_writes_do_not_create_history(team_member_client, version):
    for i in range(20):
        assert (
            post_markdown(team_member_client, version, {"readme": str(i)}).status_code
            == 200
        )
    assert (
        post_markdown(team_member_client, version, {"readme": "blocked"}).status_code
        == 429
    )
    version.refresh_from_db()
    assert version.readme_override == "19"
    assert version.markdown_revisions.count() == 20


def test_noop_does_not_change_attribution_or_other_document(
    team_member_client, version
):
    assert (
        post_markdown(team_member_client, version, {"readme": "saved"}).status_code
        == 200
    )
    version.refresh_from_db()
    editor, timestamp = (
        version.readme_override_edited_by_id,
        version.readme_override_edited_at,
    )
    other_user = UserFactory()
    TeamMemberFactory(user=other_user, team=version.package.owner, role="member")
    team_member_client.force_authenticate(other_user)
    assert (
        post_markdown(
            team_member_client, version, {"readme": "saved", "changelog": "new log"}
        ).status_code
        == 200
    )
    version.refresh_from_db()
    assert (
        version.readme_override_edited_by_id,
        version.readme_override_edited_at,
    ) == (editor, timestamp)
    assert version.changelog_override_edited_by_id == other_user.pk
    assert version.markdown_revisions.count() == 2


def test_history_documents_and_versions_do_not_leak(admin_client, version):
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
    response = admin_client.get(history_url(version))
    assert [row["content"] for row in response.json()["results"]] == ["target"]
    assert admin_client.get(history_url(version, "bogus")).status_code == 404
    assert admin_client.get(history_url(version) + "?cursor=invalid").status_code == 404
