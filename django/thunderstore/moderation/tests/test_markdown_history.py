"""Exercise markdown history integrity, access control, and bounded reads."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.db import IntegrityError, connection, connections, transaction
from django.test.utils import CaptureQueriesContext

from thunderstore.api.cyberstorm.services.package_version import (
    update_markdown_overrides,
)
from thunderstore.api.cyberstorm.tests.utils import (
    get_resolver,
    get_schema,
    history_url,
    markdown_url,
    post_markdown,
    validate_response_against_schema,
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


@pytest.fixture
def staff_client(api_client):
    api_client.force_authenticate(UserFactory(is_staff=True))
    return api_client


def test_history_response_schema(staff_client, version):
    schema = get_schema(staff_client)
    response = staff_client.get(history_url(version))
    path = "/moderation/api/package/{namespace_id}/{package_name}/v/{version_number}/markdown/{document}/history/"
    assert (
        validate_response_against_schema(
            response, path, "get", schema, get_resolver(schema)
        )
        == []
    )


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
    staff_client, version
):
    PackageVersion.objects.filter(pk=version.pk).update(is_active=False)
    assert staff_client.get(history_url(version)).status_code == 200
    assert (
        staff_client.get(f"{markdown_url(version)}readme/download/").status_code == 404
    )


def test_history_pagination_survives_new_saves(staff_client, version):
    rows = PackageVersionMarkdownRevision.objects.bulk_create(
        [
            PackageVersionMarkdownRevision(
                version=version, document="readme", content=str(i), is_override=True
            )
            for i in range(35)
        ]
    )
    response = staff_client.get(history_url(version))
    assert response.status_code == 200
    assert response.json()["original"]["content"] == version.readme
    seen = [row["id"] for row in response.json()["results"]]
    version.markdown_revisions.create(
        document="readme", content="new arrival", is_override=True
    )
    while response.json()["next"]:
        response = staff_client.get(response.json()["next"])
        seen.extend(row["id"] for row in response.json()["results"])
    assert seen == [row.pk for row in reversed(rows)]
    assert len(seen) == len(set(seen))


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


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("second_content", ["first", "second"])
def test_concurrent_saves_follow_lock_order(second_content):
    version = PackageVersionFactory(readme="original")
    user = UserFactory()
    TeamMemberFactory(user=user, team=version.package.owner, role="owner")
    locking = Event()

    def observe_lock(execute, sql, params, many, context):
        if "FOR UPDATE" in sql:
            locking.set()
        return execute(sql, params, many, context)

    def save_second():
        try:
            with connection.execute_wrapper(observe_lock):
                update_markdown_overrides(user, version, {"readme": second_content})
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=1) as executor:
        with transaction.atomic():
            PackageVersion.objects.select_for_update().get(pk=version.pk)
            pending = executor.submit(save_second)
            assert locking.wait(5)
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
    response = post_markdown(
        team_member_client,
        version,
        {"readme": "old version edit", "changelog": "old log edit"},
    )
    assert response.status_code == 200
    new = PackageVersionFactory(
        package=version.package,
        name=version.name,
        version_number="2.0.0",
        readme="new packaged readme",
        changelog=None,
    )
    # Public endpoints intentionally retain their cache until expiry.
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

    for changelog, has_changelog in (("new log edit", True), (None, False)):
        response = post_markdown(team_member_client, new, {"changelog": changelog})
        assert response.status_code == 200
        cache.clear()
        listing_data = team_member_client.get(listing_url).json()
        assert listing_data["has_changelog"] is has_changelog


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
    assert staff_client.get(history_url(version, "bogus")).status_code == 404
    assert staff_client.get(history_url(version) + "?cursor=invalid").status_code == 404
