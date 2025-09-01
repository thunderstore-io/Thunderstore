from typing import Optional

import pytest
from django.http import Http404
from rest_framework.test import APIClient

from thunderstore.api.cyberstorm.views.markdown import get_package_version
from thunderstore.repository.factories import PackageVersionFactory
from thunderstore.repository.models import Package


@pytest.mark.django_db
@pytest.mark.parametrize("requested_version", (None, "1.0.0", "1.0.1", "1.2.3"))
def test_get_package_version__returns_requested_version_or_latest_by_default(
    package: Package,
    requested_version: Optional[str],
) -> None:
    PackageVersionFactory(package=package, version_number="1.0.0")
    PackageVersionFactory(package=package, version_number="1.2.3")
    PackageVersionFactory(package=package, version_number="1.0.1")

    actual = get_package_version(
        package.namespace.name,
        package.name,
        requested_version,
    )

    if requested_version:
        assert actual.version_number == requested_version
    else:
        assert actual.version_number == "1.2.3"  # latest


@pytest.mark.django_db
def test_get_package_version__raises_for_inactive_package(
    package: Package,
) -> None:
    PackageVersionFactory(package=package)
    package.is_active = False
    package.save()

    with pytest.raises(Http404):
        get_package_version(package.namespace.name, package.name, None)


@pytest.mark.django_db
@pytest.mark.parametrize("requested_version", (None, "1.0.0"))
def test_get_package_version__raises_for_inactive_package_version(
    package: Package,
    requested_version: Optional[str],
) -> None:
    PackageVersionFactory(package=package, is_active=False)

    with pytest.raises(Http404):
        get_package_version(
            package.namespace.name,
            package.name,
            requested_version,
        )


@pytest.mark.django_db
def test_readme_api_view__prerenders_markup(api_client: APIClient) -> None:
    v = PackageVersionFactory(readme="# Very **strong** header")

    response = api_client.get(
        f"/api/cyberstorm/package/{v.package.namespace}/{v.package.name}/latest/readme/",
    )
    actual = response.json()
    expected_html = '<h1 id="user-content-very-strong-header">Very <strong>strong</strong> header</h1>\n'
    assert actual["html"] == expected_html


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("markdown", "markup"),
    (
        ("", ""),
        ("Oh hai!", "<p>Oh hai!</p>\n"),
    ),
)
def test_changelog_api_view__prerenders_markup(
    api_client: APIClient,
    markdown: Optional[str],
    markup: str,
) -> None:
    v = PackageVersionFactory(changelog=markdown)

    response = api_client.get(
        f"/api/cyberstorm/package/{v.package.namespace}/{v.package.name}/latest/changelog/",
    )
    actual = response.json()

    assert actual["html"] == markup


@pytest.mark.django_db
def test_changelog_api_view__when_package_has_no_changelog__returns_404(
    api_client: APIClient,
) -> None:
    v = PackageVersionFactory(changelog=None)

    response = api_client.get(
        f"/api/cyberstorm/package/{v.package.namespace}/{v.package.name}/latest/changelog/",
    )
    actual = response.json()

    assert response.status_code == 404
    assert actual["detail"] == "Not found."
