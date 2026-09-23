from unittest.mock import patch

import pytest

from thunderstore.api.cyberstorm.tests.utils import (
    delete_markdown,
    markdown_url,
    update_markdown,
)
from thunderstore.core.factories import UserFactory
from thunderstore.repository.factories import PackageVersionFactory
from thunderstore.repository.models import PackageVersionMarkdownRevision


@pytest.mark.django_db
def test_write_readme_override(team_member_client, version):
    response = update_markdown(
        team_member_client, version, "readme", {"content": "# New"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_edited"] is True
    assert data["edited_at"] is not None

    version.refresh_from_db()
    assert version.readme_override == "# New"
    assert version.readme_override_edited_by is not None
    assert version.readme == "Original readme"


@pytest.mark.django_db
def test_delete_discards_override_and_leaves_others_untouched(
    team_member_client, version
):
    update_markdown(team_member_client, version, "readme", {"content": "# New"})
    update_markdown(team_member_client, version, "changelog", {"content": "# Log"})
    response = delete_markdown(team_member_client, version, "readme")

    assert response.status_code == 204

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

    update_markdown(team_member_client, version, "changelog", {"content": "# Log"})

    response = team_member_client.get(changelog_url)
    assert response.status_code == 200
    assert response.json()["html"] == "<h1>Log</h1>\n"
    assert response.json()["is_edited"] is True


@pytest.mark.django_db
def test_changelog_is_only_editable_on_latest_version(team_member_client, version):
    PackageVersionFactory(
        package=version.package, name=version.name, version_number="99.0.0"
    )
    version.package.refresh_from_db()
    assert version.package.latest_id != version.pk

    response = update_markdown(
        team_member_client, version, "changelog", {"content": "# Log"}
    )
    assert response.status_code == 400
    assert delete_markdown(team_member_client, version, "changelog").status_code == 400

    response = update_markdown(
        team_member_client, version, "readme", {"content": "# Old"}
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_write_requires_team_membership(version, api_client):
    response = update_markdown(api_client, version, "readme", {"content": "# New"})
    assert response.status_code == 401

    api_client.force_authenticate(user=UserFactory())
    response = update_markdown(api_client, version, "readme", {"content": "# New"})
    assert response.status_code == 403
    assert delete_markdown(api_client, version, "readme").status_code == 403

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
        response = update_markdown(
            team_member_client, version, "readme", {"content": "# New"}
        )

    assert response.status_code == 200
    mocked_invalidate.assert_not_called()

    package.refresh_from_db()
    assert package.date_updated == date_updated
    assert package.latest_id == latest_id


@pytest.mark.django_db
def test_download_serves_only_override_content(team_member_client, version):
    url = f"{markdown_url(version)}readme/download/"
    assert team_member_client.get(url).status_code == 404

    update_markdown(
        team_member_client, version, "readme", {"content": "# Downloadable"}
    )

    response = team_member_client.get(url)
    assert response.status_code == 200
    assert response["Content-Type"] == "text/markdown; charset=utf-8"
    assert 'filename="README.md"' in response["Content-Disposition"]
    assert response.content.decode() == "# Downloadable"

    bogus_url = f"{markdown_url(version)}bogus/download/"
    assert team_member_client.get(bogus_url).status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize("deactivate_package", [True, False])
@pytest.mark.parametrize("document", ["readme", "changelog"])
def test_inactive_markdown_is_not_accessible(
    team_member_client, version, deactivate_package, document
):
    response = update_markdown(
        team_member_client, version, document, {"content": "# Edit"}
    )
    assert response.status_code == 200
    revisions = PackageVersionMarkdownRevision.objects.filter(version=version)
    revision_count = revisions.count()
    target = version.package if deactivate_package else version
    target.is_active = False
    target.save(update_fields=["is_active"])

    response = team_member_client.get(f"{markdown_url(version)}{document}/download/")
    assert response.status_code == 404
    response = update_markdown(
        team_member_client, version, document, {"content": "# Hidden edit"}
    )
    assert response.status_code == 404
    assert delete_markdown(team_member_client, version, document).status_code == 404

    version.refresh_from_db()
    assert getattr(version, f"{document}_override") == "# Edit"
    assert revisions.count() == revision_count
