import json

import pytest
from rest_framework.test import APIClient

from thunderstore.core.factories import UserFactory
from thunderstore.repository.factories import TeamMemberFactory
from thunderstore.repository.models import (
    Package,
    PackageVersion,
    PackageWiki,
    TeamMemberRole,
)
from thunderstore.wiki.factories import WikiPageFactory
from thunderstore.wiki.models import WikiPage


@pytest.mark.django_db
def test_api_experimental_package_wiki_get_404(
    package: Package,
    api_client: APIClient,
):
    response = api_client.get(
        f"/api/experimental/package/{package.owner.name}/{package.name}/wiki/",
        HTTP_ACCEPT="application/json",
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_api_experimental_package_wiki_get_success(
    package: Package,
    package_wiki: PackageWiki,
    api_client: APIClient,
):
    pages = [WikiPageFactory(wiki=package_wiki.wiki)]
    response = api_client.get(
        f"/api/experimental/package/{package.owner.name}/{package.name}/wiki/",
        HTTP_ACCEPT="application/json",
    )
    assert response.status_code == 200
    result = response.json()
    expected = {
        "id": str(package_wiki.wiki.pk),
        "title": package_wiki.wiki.title,
        "slug": package_wiki.wiki.full_slug,
        "pages": [
            {
                "id": str(p.pk),
                "title": p.title,
                "slug": p.full_slug,
                "datetime_created": p.datetime_created.isoformat().replace(
                    "+00:00", "Z"
                ),
                "datetime_updated": p.datetime_updated.isoformat().replace(
                    "+00:00", "Z"
                ),
            }
            for p in pages
        ],
    }
    assert result == expected


@pytest.mark.django_db
def test_api_experimental_package_wiki_page_create(
    package_version: PackageVersion,
    api_client: APIClient,
):
    package = package_version.package
    user = UserFactory.create()
    TeamMemberFactory.create(
        user=user,
        team=package.owner,
        role=TeamMemberRole.member,
    )

    title = "Test Page"
    content = "# This is a test page"
    assert PackageWiki.get_for_package(package, False, False) is None

    def make_request():
        return api_client.post(
            f"/api/experimental/package/{package.owner.name}/{package.name}/wiki/",
            json.dumps(
                {
                    "title": title,
                    "markdown_content": content,
                }
            ),
            content_type="application/json",
        )

    response = make_request()
    assert response.status_code == 403
    api_client.force_authenticate(user)
    response = make_request()

    assert response.status_code == 200
    wiki = PackageWiki.get_for_package(package, False, False)
    assert wiki is not None
    assert wiki.wiki.pages.count() == 1
    page = wiki.wiki.pages.first()

    result = response.json()
    assert result["id"] == str(page.pk)
    assert result["title"] == title
    assert result["title"] == page.title
    assert result["markdown_content"] == content
    assert result["markdown_content"] == page.markdown_content


@pytest.mark.django_db
def test_api_experimental_package_wiki_page_update(
    package_version: PackageVersion,
    package_wiki: PackageWiki,
    api_client: APIClient,
):
    package = package_version.package
    assert package == package_wiki.package

    user = UserFactory.create()
    TeamMemberFactory.create(
        user=user,
        team=package.owner,
        role=TeamMemberRole.member,
    )

    page = WikiPageFactory(wiki=package_wiki.wiki)
    title = "Edited Title"
    content = "# Edited Content"
    assert page.title != title
    assert page.markdown_content != content
    assert PackageWiki.get_for_package(package, False, False).wiki == page.wiki

    def make_request(page_id: int):
        return api_client.post(
            f"/api/experimental/package/{package.owner.name}/{package.name}/wiki/",
            json.dumps(
                {
                    "id": str(page_id),
                    "title": title,
                    "markdown_content": content,
                }
            ),
            content_type="application/json",
        )

    response = make_request(page.id)
    assert response.status_code == 403
    api_client.force_authenticate(user)
    response = make_request(WikiPageFactory().pk)
    assert response.status_code == 404
    response = make_request(page.id)

    assert response.status_code == 200
    wiki = PackageWiki.get_for_package(package, False, False)
    assert wiki is not None
    assert wiki.wiki.pages.count() == 1
    page = wiki.wiki.pages.first()

    result = response.json()
    page.refresh_from_db()
    assert result["id"] == str(page.pk)
    assert result["title"] == title
    assert page.title == title
    assert result["markdown_content"] == content
    assert page.markdown_content == content


@pytest.mark.django_db
def test_api_experimental_package_wiki_page_delete(
    package_version: PackageVersion,
    package_wiki: PackageWiki,
    api_client: APIClient,
):
    package = package_version.package
    assert package == package_wiki.package

    user = UserFactory.create()
    TeamMemberFactory.create(
        user=user,
        team=package.owner,
        role=TeamMemberRole.member,
    )

    page = WikiPageFactory(wiki=package_wiki.wiki)
    assert PackageWiki.get_for_package(package, False, False).wiki == page.wiki

    def make_request(page_id: int):
        return api_client.delete(
            f"/api/experimental/package/{package.owner.name}/{package.name}/wiki/",
            json.dumps({"id": str(page_id)}),
            content_type="application/json",
        )

    response = make_request(page.id)
    assert response.status_code == 403
    api_client.force_authenticate(user)
    response = make_request(WikiPageFactory().pk)
    assert response.status_code == 404
    response = make_request(page.id)

    assert response.status_code == 200
    wiki = PackageWiki.get_for_package(package, False, False)
    assert wiki is not None
    assert wiki.wiki.pages.count() == 0

    result = response.json()
    assert result == {"success": True}
    assert WikiPage.objects.filter(pk=page.pk).first() is None
