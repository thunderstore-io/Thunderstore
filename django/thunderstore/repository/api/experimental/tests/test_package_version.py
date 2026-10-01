from typing import Optional

import pytest
from rest_framework.test import APIClient

from thunderstore.repository.models import PackageVersion


@pytest.mark.django_db
@pytest.mark.parametrize("changelog", (None, "# Test changelog"))
def test_api_experimental_package_version_changelog(
    api_client: APIClient, package_version: PackageVersion, changelog: Optional[str]
) -> None:
    package_version.changelog = changelog
    package_version.save()
    response = api_client.get(
        f"/api/experimental/package/"
        f"{package_version.package.owner.name}/"
        f"{package_version.package.name}/"
        f"{package_version.version_number}/"
        "changelog/"
    )
    assert response.status_code == 200
    result = response.json()
    assert result["markdown"] == changelog


@pytest.mark.django_db
def test_api_experimental_package_version_changelog_uses_override(
    api_client: APIClient,
    package_version: PackageVersion,
) -> None:
    package_version.changelog = "Base changelog"
    package_version.changelog_override = "Override changelog"
    package_version.save()

    response = api_client.get(
        f"/api/experimental/package/"
        f"{package_version.package.owner.name}/"
        f"{package_version.package.name}/"
        f"{package_version.version_number}/"
        "changelog/"
    )
    assert response.status_code == 200
    result = response.json()
    assert result["markdown"] == "Override changelog"


@pytest.mark.django_db
@pytest.mark.parametrize("readme", ("", "# Test readme"))
def test_api_experimental_package_version_readme(
    api_client: APIClient, package_version: PackageVersion, readme: Optional[str]
) -> None:
    package_version.readme = readme
    package_version.save()
    response = api_client.get(
        f"/api/experimental/package/"
        f"{package_version.package.owner.name}/"
        f"{package_version.package.name}/"
        f"{package_version.version_number}/"
        "readme/"
    )
    assert response.status_code == 200
    result = response.json()
    assert result["markdown"] == readme


@pytest.mark.django_db
def test_api_experimental_package_version_readme_uses_override(
    api_client: APIClient,
    package_version: PackageVersion,
) -> None:
    package_version.readme = "Base readme"
    package_version.readme_override = "Override readme"
    package_version.save()

    response = api_client.get(
        f"/api/experimental/package/"
        f"{package_version.package.owner.name}/"
        f"{package_version.package.name}/"
        f"{package_version.version_number}/"
        "readme/"
    )
    assert response.status_code == 200
    result = response.json()
    assert result["markdown"] == "Override readme"
