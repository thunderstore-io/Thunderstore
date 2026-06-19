import json
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import TestUserTypes
from thunderstore.api.cyberstorm.tests.utils import validate_max_queries
from thunderstore.community.factories import (
    CommunityFactory,
    ModeratorNoteFactory,
    PackageListingFactory,
)
from thunderstore.community.models import (
    CommunityMemberRole,
    CommunityMembership,
    ModeratorNote,
    PackageListing,
)
from thunderstore.core.factories import UserFactory
from thunderstore.repository.factories import PackageVersionFactory

CREATE_STATUS_MAP = {
    TestUserTypes.no_user: 401,
    TestUserTypes.unauthenticated: 401,
    TestUserTypes.regular_user: 403,
    TestUserTypes.deactivated_user: 403,
    TestUserTypes.service_account: 403,
    TestUserTypes.site_admin: 201,
    TestUserTypes.superuser: 201,
}

WRITE_STATUS_MAP = {
    TestUserTypes.no_user: 401,
    TestUserTypes.unauthenticated: 401,
    TestUserTypes.regular_user: 403,
    TestUserTypes.deactivated_user: 403,
    TestUserTypes.service_account: 403,
    TestUserTypes.site_admin: 200,
    TestUserTypes.superuser: 200,
}


def _authenticate(api_client: APIClient, user_type: str):
    user = TestUserTypes.get_user_by_type(user_type)
    if user_type not in TestUserTypes.fake_users():
        api_client.force_authenticate(user=user)
    return user


def _listing_notes_url(listing: PackageListing) -> str:
    return (
        f"/api/cyberstorm/listing/{listing.community.identifier}/"
        f"{listing.package.namespace.name}/{listing.package.name}/notes/"
    )


def _version_notes_url(listing: PackageListing, version_number: str) -> str:
    return (
        f"/api/cyberstorm/listing/{listing.community.identifier}/"
        f"{listing.package.namespace.name}/{listing.package.name}/"
        f"v/{version_number}/notes/"
    )


def _community_notes_url(community) -> str:
    return f"/api/cyberstorm/community/{community.identifier}/notes/"


def _detail_url(note_id: int) -> str:
    return f"/api/cyberstorm/moderator-note/{note_id}/"


# --- Create: permissions -----------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
def test_create_community_note_permissions(api_client, community, user_type):
    _authenticate(api_client, user_type)
    response = api_client.post(
        _community_notes_url(community),
        data=json.dumps({"content": "Heads up"}),
        content_type="application/json",
    )
    assert response.status_code == CREATE_STATUS_MAP[user_type]
    if response.status_code == 201:
        assert community.moderator_notes.count() == 1
        assert response.json()["content"] == "Heads up"
        assert response.json()["target_type"] == "community"


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
def test_create_listing_note_permissions(api_client, active_package_listing, user_type):
    _authenticate(api_client, user_type)
    response = api_client.post(
        _listing_notes_url(active_package_listing),
        data=json.dumps({"content": "Known issue"}),
        content_type="application/json",
    )
    assert response.status_code == CREATE_STATUS_MAP[user_type]
    if response.status_code == 201:
        assert active_package_listing.moderator_notes.count() == 1
        assert response.json()["target_type"] == "listing"


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
def test_create_version_note_permissions(api_client, active_package_listing, user_type):
    version = active_package_listing.package.versions.first()
    _authenticate(api_client, user_type)
    response = api_client.post(
        _version_notes_url(active_package_listing, version.version_number),
        data=json.dumps({"content": "Broken in this build"}),
        content_type="application/json",
    )
    assert response.status_code == CREATE_STATUS_MAP[user_type]
    if response.status_code == 201:
        note = active_package_listing.moderator_notes.get()
        assert note.package_version_id == version.pk
        assert response.json()["target_type"] == "version"
        assert response.json()["version_number"] == version.version_number


# --- Create: validation / 404 ------------------------------------------------


@pytest.mark.django_db
def test_create_listing_note_requires_content(api_client, active_package_listing):
    _authenticate(api_client, TestUserTypes.superuser)
    response = api_client.post(
        _listing_notes_url(active_package_listing),
        data=json.dumps({}),
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.json() == {"content": ["This field is required."]}


@pytest.mark.django_db
@pytest.mark.parametrize(
    "invalid_field", ["community_id", "namespace_id", "package_name"]
)
def test_create_listing_note_404(api_client, active_package_listing, invalid_field):
    community_id = active_package_listing.community.identifier
    namespace_id = active_package_listing.package.namespace.name
    package_name = active_package_listing.package.name
    if invalid_field == "community_id":
        community_id = "invalid"
    elif invalid_field == "namespace_id":
        namespace_id = "invalid"
    else:
        package_name = "invalid"

    _authenticate(api_client, TestUserTypes.superuser)
    response = api_client.post(
        f"/api/cyberstorm/listing/{community_id}/{namespace_id}/{package_name}/notes/",
        data=json.dumps({"content": "x"}),
        content_type="application/json",
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_create_version_note_404_for_unknown_version(
    api_client, active_package_listing
):
    _authenticate(api_client, TestUserTypes.superuser)
    response = api_client.post(
        _version_notes_url(active_package_listing, "9.9.9"),
        data=json.dumps({"content": "x"}),
        content_type="application/json",
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_create_community_note_404_for_unknown_community(api_client):
    _authenticate(api_client, TestUserTypes.superuser)
    response = api_client.post(
        "/api/cyberstorm/community/does-not-exist/notes/",
        data=json.dumps({"content": "x"}),
        content_type="application/json",
    )
    assert response.status_code == 404


# --- Update / delete ---------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
def test_update_note_permissions(api_client, community, user_type):
    note = ModeratorNoteFactory(community=community, content="Original")
    _authenticate(api_client, user_type)
    response = api_client.patch(
        _detail_url(note.pk),
        data=json.dumps({"content": "Edited"}),
        content_type="application/json",
    )
    assert response.status_code == WRITE_STATUS_MAP[user_type]
    note.refresh_from_db()
    if response.status_code == 200:
        assert note.content == "Edited"
        assert response.json()["content"] == "Edited"
    else:
        assert note.content == "Original"


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
def test_delete_note_permissions(api_client, community, user_type):
    note = ModeratorNoteFactory(community=community)
    _authenticate(api_client, user_type)
    response = api_client.delete(_detail_url(note.pk))

    expected = WRITE_STATUS_MAP[user_type]
    expected = 204 if expected == 200 else expected
    assert response.status_code == expected
    if response.status_code == 204:
        assert not ModeratorNote.objects.filter(pk=note.pk).exists()
    else:
        assert ModeratorNote.objects.filter(pk=note.pk).exists()


@pytest.mark.django_db
def test_update_note_404_for_unknown_note(api_client):
    _authenticate(api_client, TestUserTypes.superuser)
    response = api_client.patch(
        _detail_url(999999),
        data=json.dumps({"content": "x"}),
        content_type="application/json",
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_community_moderator_cannot_edit_foreign_community_note(api_client):
    foreign_note = ModeratorNoteFactory(community=CommunityFactory())
    moderator = UserFactory()
    CommunityMembership.objects.create(
        user=moderator,
        community=CommunityFactory(),
        role=CommunityMemberRole.moderator,
    )

    api_client.force_authenticate(user=moderator)
    response = api_client.patch(
        _detail_url(foreign_note.pk),
        data=json.dumps({"content": "Edited"}),
        content_type="application/json",
    )
    assert response.status_code == 403
    foreign_note.refresh_from_db()
    assert foreign_note.content != "Edited"


# --- Caching / data-leak guards ----------------------------------------------


@pytest.mark.django_db
def test_write_endpoint_is_not_publicly_cached(api_client, active_package_listing):
    _authenticate(api_client, TestUserTypes.superuser)
    response = api_client.post(
        _listing_notes_url(active_package_listing),
        data=json.dumps({"content": "x"}),
        content_type="application/json",
    )
    assert response.status_code == 201
    assert "public" not in (response.get("Cache-Control") or "")


@pytest.mark.django_db
def test_community_detail_embeds_note_for_anonymous_and_is_public(
    api_client, community
):
    ModeratorNoteFactory(community=community, content="Server outage")

    # No authentication: the note is fully public.
    response = api_client.get(f"/api/cyberstorm/community/{community.identifier}/")
    assert response.status_code == 200
    assert "public" in (response.get("Cache-Control") or "")
    assert response.json()["moderator_notes"][0]["content"] == "Server outage"


@pytest.mark.django_db
def test_community_detail_notes_empty_when_absent(api_client, community):
    response = api_client.get(f"/api/cyberstorm/community/{community.identifier}/")
    assert response.status_code == 200
    assert response.json()["moderator_notes"] == []


# --- Read embed: active notes list -------------------------------------------


@pytest.mark.django_db
def test_listing_detail_embeds_listing_note(api_client, active_package_listing):
    ModeratorNoteFactory(package_listing=active_package_listing, content="Heads up")
    response = api_client.get(_listing_detail_url(active_package_listing))
    assert response.status_code == 200
    notes = response.json()["moderator_notes"]
    assert [n["content"] for n in notes] == ["Heads up"]
    assert notes[0]["is_active"] is True


@pytest.mark.django_db
def test_listing_detail_notes_empty_when_absent(api_client, active_package_listing):
    response = api_client.get(_listing_detail_url(active_package_listing))
    assert response.status_code == 200
    assert response.json()["moderator_notes"] == []


@pytest.mark.django_db
def test_version_note_resolves_per_version(api_client, active_package_listing):
    listing = active_package_listing
    v1 = listing.package.versions.get(version_number="1.0.0")
    v2 = PackageVersionFactory(
        package=listing.package,
        name=listing.package.name,
        version_number="1.0.1",
        is_active=True,
    )
    ModeratorNoteFactory(package_listing=listing, package_version=v1, content="v1 only")
    ModeratorNoteFactory(package_listing=listing, package_version=v2, content="v2 only")

    base = (
        f"/api/cyberstorm/listing/{listing.community.identifier}/"
        f"{listing.package.namespace.name}/{listing.package.name}"
    )

    def contents(url):
        return [n["content"] for n in api_client.get(url).json()["moderator_notes"]]

    assert contents(f"{base}/v/1.0.0/") == ["v1 only"]
    assert contents(f"{base}/v/1.0.1/") == ["v2 only"]


@pytest.mark.django_db
def test_listing_wide_and_version_notes_both_shown(api_client, active_package_listing):
    # With multiple active notes, the listing-wide note and the viewed version's
    # note are both surfaced (there is no single-note priority anymore).
    listing = active_package_listing
    version = listing.package.versions.get(version_number="1.0.0")
    ModeratorNoteFactory(package_listing=listing, content="Listing wide")
    ModeratorNoteFactory(
        package_listing=listing, package_version=version, content="Version note"
    )

    base = (
        f"/api/cyberstorm/listing/{listing.community.identifier}/"
        f"{listing.package.namespace.name}/{listing.package.name}"
    )

    def contents(url):
        return {n["content"] for n in api_client.get(url).json()["moderator_notes"]}

    assert contents(f"{base}/") == {"Listing wide", "Version note"}
    assert contents(f"{base}/v/1.0.0/") == {"Listing wide", "Version note"}


@pytest.mark.django_db
def test_latest_version_note_shows_on_listing_until_superseded(
    api_client, active_package_listing
):
    # A version note rides the listing page while it's the latest, and drops off
    # once a newer version (without a note) is uploaded.
    listing = active_package_listing
    v1 = listing.package.versions.get(version_number="1.0.0")
    ModeratorNoteFactory(
        package_listing=listing, package_version=v1, content="v1 issue"
    )

    url = _listing_detail_url(listing)
    assert [n["content"] for n in api_client.get(url).json()["moderator_notes"]] == [
        "v1 issue"
    ]

    # A newer version with no note supersedes it: the listing page note clears.
    PackageVersionFactory(
        package=listing.package,
        name=listing.package.name,
        version_number="1.0.1",
        is_active=True,
    )
    assert api_client.get(url).json()["moderator_notes"] == []


@pytest.mark.django_db
def test_note_does_not_leak_across_communities(api_client, active_package_listing):
    listing = active_package_listing
    ModeratorNoteFactory(package_listing=listing, content="Only in community A")

    other_community = CommunityFactory()
    PackageListing.objects.create(community=other_community, package=listing.package)

    resp_a = api_client.get(_listing_detail_url(listing))
    assert [n["content"] for n in resp_a.json()["moderator_notes"]] == [
        "Only in community A"
    ]

    resp_b = api_client.get(
        f"/api/cyberstorm/listing/{other_community.identifier}/"
        f"{listing.package.namespace.name}/{listing.package.name}/"
    )
    assert resp_b.status_code == 200
    assert resp_b.json()["moderator_notes"] == []


@pytest.mark.django_db
def test_inactive_note_is_not_shown_publicly(api_client, active_package_listing):
    note = ModeratorNoteFactory(
        package_listing=active_package_listing, content="Off", is_active=False
    )
    response = api_client.get(_listing_detail_url(active_package_listing))
    assert response.json()["moderator_notes"] == []
    assert ModeratorNote.objects.filter(pk=note.pk).exists()


@pytest.mark.django_db
def test_listing_detail_note_query_budget(api_client, active_package_listing):
    # One active listing-wide note plus active notes on several versions: the
    # prefetch must load them in a bounded number of queries (no N+1).
    listing = active_package_listing
    ModeratorNoteFactory(package_listing=listing, content="Listing wide")
    for i in range(3):
        version = PackageVersionFactory(
            package=listing.package,
            name=listing.package.name,
            version_number=f"2.0.{i}",
            is_active=True,
        )
        ModeratorNoteFactory(
            package_listing=listing, package_version=version, content=f"v {i}"
        )

    response = validate_max_queries(
        client=api_client,
        method="get",
        path=_listing_detail_url(listing),
        max_queries=15,
    )
    contents = [n["content"] for n in response.json()["moderator_notes"]]
    # The listing-wide note plus the latest version's note (2.0.2 is latest).
    assert "Listing wide" in contents
    assert "v 2" in contents


def _make_community_moderator(community):
    user = UserFactory()
    CommunityMembership.objects.create(
        user=user,
        community=community,
        role=CommunityMemberRole.moderator,
    )
    return user


def _listing_detail_url(listing: PackageListing) -> str:
    return (
        f"/api/cyberstorm/listing/{listing.community.identifier}/"
        f"{listing.package.namespace.name}/{listing.package.name}/"
    )


@pytest.mark.django_db
@pytest.mark.parametrize("method", ["patch", "delete"])
def test_listing_note_detail_cross_community_forbidden(api_client, method):
    # A LISTING-target note: authority must resolve through
    # package_listing.community, not the note's (null) community FK.
    listing = PackageListingFactory()
    note = ModeratorNoteFactory(package_listing=listing, content="Original")
    foreign_moderator = _make_community_moderator(CommunityFactory())
    api_client.force_authenticate(user=foreign_moderator)

    if method == "patch":
        response = api_client.patch(
            _detail_url(note.pk),
            data=json.dumps({"content": "Edited"}),
            content_type="application/json",
        )
    else:
        response = api_client.delete(_detail_url(note.pk))

    assert response.status_code == 403
    note.refresh_from_db()
    assert note.content == "Original"
    assert ModeratorNote.objects.filter(pk=note.pk).exists()


@pytest.mark.django_db
def test_create_version_note_404_for_foreign_package_version(
    api_client, active_package_listing
):
    # A version that exists, but on a different package, must not be smuggled
    # onto this listing: the view scopes the lookup to listing.package.versions.
    foreign_version = PackageVersionFactory(
        package=PackageListingFactory().package,
        version_number="9.8.7",
        is_active=True,
    )
    _authenticate(api_client, TestUserTypes.superuser)
    response = api_client.post(
        _version_notes_url(active_package_listing, foreign_version.version_number),
        data=json.dumps({"content": "x"}),
        content_type="application/json",
    )
    assert response.status_code == 404
    assert not active_package_listing.moderator_notes.exists()


@pytest.mark.django_db
def test_notes_hidden_on_rejected_listing(api_client, rejected_package_listing):
    ModeratorNoteFactory(
        package_listing=rejected_package_listing, content="Hidden note"
    )
    url = _listing_detail_url(rejected_package_listing)

    # Anonymous: the whole rejected listing 404s, so the note never serializes.
    anon = api_client.get(url)
    assert anon.status_code == 404

    # A moderator can view the rejected listing and sees the note.
    api_client.force_authenticate(
        user=TestUserTypes.get_user_by_type(TestUserTypes.superuser)
    )
    mod = api_client.get(url)
    assert mod.status_code == 200
    assert [n["content"] for n in mod.json()["moderator_notes"]] == ["Hidden note"]


@pytest.mark.django_db
def test_public_detail_does_not_leak_internal_notes(api_client, active_package_listing):
    # The moderator-internal PackageListing.notes field must never appear in the
    # public detail payload alongside the public moderator_notes.
    active_package_listing.notes = "INTERNAL SECRET"
    active_package_listing.save(update_fields=("notes",))
    ModeratorNoteFactory(package_listing=active_package_listing, content="Public note")

    response = api_client.get(_listing_detail_url(active_package_listing))
    assert response.status_code == 200
    assert "INTERNAL SECRET" not in response.content.decode()
    assert [n["content"] for n in response.json()["moderator_notes"]] == ["Public note"]


@pytest.mark.django_db
def test_update_note_bumps_datetime_updated(api_client, community):
    note = ModeratorNoteFactory(community=community, content="Original")
    original_updated = note.datetime_updated

    _authenticate(api_client, TestUserTypes.superuser)
    response = api_client.patch(
        _detail_url(note.pk),
        data=json.dumps({"content": "Edited"}),
        content_type="application/json",
    )
    assert response.status_code == 200
    note.refresh_from_db()
    assert note.datetime_updated > original_updated


@pytest.mark.django_db
def test_create_keeps_previous_active_listing_note_via_http(
    api_client, active_package_listing
):
    listing = active_package_listing
    first = ModeratorNoteFactory(package_listing=listing, content="First")
    _authenticate(api_client, TestUserTypes.superuser)

    response = api_client.post(
        _listing_notes_url(listing),
        data=json.dumps({"content": "Second"}),
        content_type="application/json",
    )
    assert response.status_code == 201

    first.refresh_from_db()
    # Both notes stay active; the new one is added alongside the existing one.
    assert first.is_active is True
    assert listing.moderator_notes.filter(is_active=True).count() == 2
    contents = {
        n["content"]
        for n in api_client.get(_listing_detail_url(listing)).json()["moderator_notes"]
    }
    assert contents == {"First", "Second"}


@pytest.mark.django_db
def test_deactivate_note_via_http_hides_it(api_client, active_package_listing):
    listing = active_package_listing
    note = ModeratorNoteFactory(package_listing=listing, content="Heads up")
    _authenticate(api_client, TestUserTypes.superuser)

    response = api_client.patch(
        _detail_url(note.pk),
        data=json.dumps({"is_active": False}),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert api_client.get(_listing_detail_url(listing)).json()["moderator_notes"] == []


@pytest.mark.django_db
def test_community_list_omits_moderator_note(api_client, community):
    ModeratorNoteFactory(community=community, content="Community note")

    response = api_client.get("/api/cyberstorm/community/?include_unlisted=true")
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) >= 1
    for item in results:
        assert "moderator_note" not in item
        assert "moderator_notes" not in item


# --- Moderator read (GET, includes inactive) ---------------------------------

GET_STATUS_MAP = {
    TestUserTypes.no_user: 401,
    TestUserTypes.unauthenticated: 401,
    TestUserTypes.regular_user: 403,
    TestUserTypes.deactivated_user: 403,
    TestUserTypes.service_account: 403,
    TestUserTypes.site_admin: 200,
    TestUserTypes.superuser: 200,
}


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
def test_get_listing_note_permissions(api_client, active_package_listing, user_type):
    ModeratorNoteFactory(package_listing=active_package_listing, content="Heads up")
    _authenticate(api_client, user_type)
    response = api_client.get(_listing_notes_url(active_package_listing))
    assert response.status_code == GET_STATUS_MAP[user_type]
    if response.status_code == 200:
        assert [n["content"] for n in response.json()["moderator_notes"]] == [
            "Heads up"
        ]


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
def test_get_community_note_permissions(api_client, community, user_type):
    ModeratorNoteFactory(community=community, content="Outage")
    _authenticate(api_client, user_type)
    response = api_client.get(_community_notes_url(community))
    assert response.status_code == GET_STATUS_MAP[user_type]
    if response.status_code == 200:
        assert [n["content"] for n in response.json()["moderator_notes"]] == ["Outage"]


@pytest.mark.django_db
def test_get_includes_inactive_so_it_can_be_reactivated(
    api_client, active_package_listing
):
    # Unlike the public listing detail (active-only), the moderator read surfaces
    # deactivated notes too, so the UI can offer "Activate".
    ModeratorNoteFactory(
        package_listing=active_package_listing, content="Off", is_active=False
    )
    _authenticate(api_client, TestUserTypes.superuser)
    response = api_client.get(_listing_notes_url(active_package_listing))
    assert response.status_code == 200
    notes = response.json()["moderator_notes"]
    assert notes[0]["content"] == "Off"
    assert notes[0]["is_active"] is False


@pytest.mark.django_db
def test_get_returns_empty_list_when_absent(api_client, active_package_listing):
    _authenticate(api_client, TestUserTypes.superuser)
    response = api_client.get(_listing_notes_url(active_package_listing))
    assert response.status_code == 200
    assert response.json()["moderator_notes"] == []


@pytest.mark.django_db
def test_get_lists_all_notes_newest_first(api_client, active_package_listing):
    older = ModeratorNoteFactory(
        package_listing=active_package_listing, content="Older", is_active=False
    )
    ModeratorNote.objects.filter(pk=older.pk).update(
        datetime_created=timezone.now() - timedelta(days=1)
    )
    ModeratorNoteFactory(package_listing=active_package_listing, content="Newer")
    _authenticate(api_client, TestUserTypes.superuser)
    response = api_client.get(_listing_notes_url(active_package_listing))
    # Both active and inactive notes are returned, newest first.
    assert [n["content"] for n in response.json()["moderator_notes"]] == [
        "Newer",
        "Older",
    ]


@pytest.mark.django_db
def test_get_listing_notes_excludes_version_notes(api_client, active_package_listing):
    version = active_package_listing.package.versions.first()
    ModeratorNoteFactory(
        package_listing=active_package_listing, package_version=version, content="V"
    )
    _authenticate(api_client, TestUserTypes.superuser)
    # The listing-wide read must not surface a version-scoped note.
    listing_resp = api_client.get(_listing_notes_url(active_package_listing))
    assert listing_resp.json()["moderator_notes"] == []
    # ...but the version read returns it.
    version_resp = api_client.get(
        _version_notes_url(active_package_listing, version.version_number)
    )
    notes = version_resp.json()["moderator_notes"]
    assert notes[0]["content"] == "V"
    assert notes[0]["target_type"] == "version"


@pytest.mark.django_db
def test_get_notes_do_not_leak_across_communities(api_client, active_package_listing):
    ModeratorNoteFactory(package_listing=active_package_listing, content="Community A")
    other_community = CommunityFactory()
    PackageListing.objects.create(
        community=other_community, package=active_package_listing.package
    )
    _authenticate(api_client, TestUserTypes.superuser)
    other_url = (
        f"/api/cyberstorm/listing/{other_community.identifier}/"
        f"{active_package_listing.package.namespace.name}/"
        f"{active_package_listing.package.name}/notes/"
    )
    assert api_client.get(other_url).json()["moderator_notes"] == []


# --- Community permissions (gates the moderator UI) --------------------------


def _community_permissions_url(community) -> str:
    return f"/api/cyberstorm/community/{community.identifier}/permissions/"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "user_type, can_moderate",
    [
        (TestUserTypes.regular_user, False),
        (TestUserTypes.service_account, False),
        (TestUserTypes.site_admin, True),
        (TestUserTypes.superuser, True),
    ],
)
def test_community_permissions_can_moderate(
    api_client, community, user_type, can_moderate
):
    _authenticate(api_client, user_type)
    response = api_client.get(_community_permissions_url(community))
    assert response.status_code == 200
    assert response.json()["permissions"]["can_moderate"] is can_moderate


@pytest.mark.django_db
def test_community_permissions_for_community_moderator(api_client, community):
    moderator = _make_community_moderator(community)
    api_client.force_authenticate(user=moderator)
    response = api_client.get(_community_permissions_url(community))
    assert response.status_code == 200
    assert response.json()["permissions"]["can_moderate"] is True


@pytest.mark.django_db
def test_community_permissions_requires_auth(api_client, community):
    assert api_client.get(_community_permissions_url(community)).status_code == 401
