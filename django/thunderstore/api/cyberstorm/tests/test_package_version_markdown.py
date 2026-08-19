import json
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from thunderstore.core.factories import UserFactory
from thunderstore.repository.factories import PackageVersionFactory, TeamMemberFactory
from thunderstore.repository.models import PackageVersion


def markdown_url(version: PackageVersion) -> str:
    return (
        f"/api/cyberstorm/package/{version.package.namespace}"
        f"/{version.package.name}/v/{version.version_number}/markdown/"
    )


def post_markdown(api_client: APIClient, version: PackageVersion, data: dict):
    return api_client.post(
        markdown_url(version),
        data=json.dumps(data),
        content_type="application/json",
    )


@pytest.fixture
def version(db) -> PackageVersion:
    return PackageVersionFactory(readme="Original readme", changelog=None)


@pytest.fixture
def team_member_client(version, api_client) -> APIClient:
    user = UserFactory()
    TeamMemberFactory(team=version.package.owner, user=user, role="owner")
    api_client.force_authenticate(user=user)
    return api_client


@pytest.mark.django_db
def test_write_readme_override(team_member_client, version):
    response = post_markdown(team_member_client, version, {"readme": "# New"})

    assert response.status_code == 200
    data = response.json()
    assert data["readme"]["html"] == "<h1>New</h1>\n"
    assert data["readme"]["is_edited"] is True
    assert data["readme"]["edited_at"] is not None
    assert data["changelog"]["is_edited"] is False

    version.refresh_from_db()
    assert version.readme_override == "# New"
    assert version.readme_override_edited_by is not None
    assert version.readme == "Original readme"


@pytest.mark.django_db
def test_null_discards_override_and_leaves_others_untouched(
    team_member_client, version
):
    post_markdown(
        team_member_client, version, {"readme": "# New", "changelog": "# Log"}
    )
    response = post_markdown(team_member_client, version, {"readme": None})

    assert response.status_code == 200
    assert response.json()["readme"]["is_edited"] is False

    version.refresh_from_db()
    assert version.readme_override is None
    assert version.readme_override_edited_at is None
    assert version.readme_override_edited_by is None
    assert version.resolved_readme == "Original readme"
    assert version.changelog_override == "# Log"


@pytest.mark.django_db
def test_changelog_override_makes_changelog_visible(team_member_client, version):
    changelog_url = (
        f"/api/cyberstorm/package/{version.package.namespace}"
        f"/{version.package.name}/latest/changelog/"
    )
    assert team_member_client.get(changelog_url).status_code == 404

    post_markdown(team_member_client, version, {"changelog": "# Log"})

    response = team_member_client.get(changelog_url)
    assert response.status_code == 200
    assert response.json()["html"] == "<h1>Log</h1>\n"


@pytest.mark.django_db
def test_changelog_is_only_editable_on_latest_version(team_member_client, version):
    PackageVersionFactory(
        package=version.package, name=version.name, version_number="99.0.0"
    )
    version.package.refresh_from_db()
    assert version.package.latest_id != version.pk

    response = post_markdown(team_member_client, version, {"changelog": "# Log"})
    assert response.status_code == 400

    response = post_markdown(team_member_client, version, {"readme": "# Old"})
    assert response.status_code == 200


@pytest.mark.django_db
def test_write_requires_team_membership(version, api_client):
    response = post_markdown(api_client, version, {"readme": "# New"})
    assert response.status_code == 401

    api_client.force_authenticate(user=UserFactory())
    response = post_markdown(api_client, version, {"readme": "# New"})
    assert response.status_code == 403

    version.refresh_from_db()
    assert version.readme_override is None


@pytest.mark.django_db
def test_write_does_not_touch_package_or_caches(team_member_client, version):
    package = version.package
    date_updated = package.date_updated
    latest_id = package.latest_id

    with patch(
        "thunderstore.repository.models.package.invalidate_cache_on_commit_async"
    ) as mocked_invalidate:
        response = post_markdown(team_member_client, version, {"readme": "# New"})

    assert response.status_code == 200
    mocked_invalidate.assert_not_called()

    package.refresh_from_db()
    assert package.date_updated == date_updated
    assert package.latest_id == latest_id


@pytest.mark.django_db
def test_download_serves_only_override_content(team_member_client, version):
    url = f"{markdown_url(version)}readme/download/"
    assert team_member_client.get(url).status_code == 404

    post_markdown(team_member_client, version, {"readme": "# Downloadable"})

    response = team_member_client.get(url)
    assert response.status_code == 200
    assert response["Content-Type"] == "text/markdown; charset=utf-8"
    assert 'filename="README.md"' in response["Content-Disposition"]
    assert response.content.decode() == "# Downloadable"

    bogus_url = f"{markdown_url(version)}bogus/download/"
    assert team_member_client.get(bogus_url).status_code == 404
