import pytest

from thunderstore.community.models import CommunitySite, PackageListing
from thunderstore.core.factories import UserFactory
from thunderstore.frontend.extract_props import extract_props_from_html
from thunderstore.markdown.templatetags.markdownify import render_markdown
from thunderstore.repository.factories import TeamMemberFactory
from thunderstore.wiki.models import WikiPage


@pytest.mark.django_db
def test_views_package_wiki_home_no_content(
    client,
    active_package_listing: PackageListing,
    community_site: CommunitySite,
) -> None:
    assert active_package_listing.package.has_wiki is False

    def get_response_text():
        response = client.get(
            active_package_listing.get_wiki_url(),
            HTTP_HOST=community_site.site.domain,
        )
        assert response.status_code == 200
        return response.content.decode("utf-8")

    response_text = get_response_text()
    assert "<p>This wiki currently has no pages in it.</p>" in response_text
    assert "Create a page" not in response_text
    assert "New page" not in response_text

    team_user = UserFactory()
    TeamMemberFactory(team=active_package_listing.package.owner, user=team_user)
    client.force_login(team_user)

    response_text = get_response_text()
    assert "<p>This wiki currently has no pages in it.</p>" in response_text
    assert "Create a page" in response_text
    assert "New page" in response_text


@pytest.mark.django_db
def test_views_package_wiki_home_with_content(
    client,
    active_package_listing: PackageListing,
    community_site: CommunitySite,
    active_package_wiki_page: WikiPage,
) -> None:
    assert active_package_listing.package.has_wiki is True
    page = active_package_wiki_page

    def get_response_text():
        response = client.get(
            active_package_listing.get_wiki_url(),
            HTTP_HOST=community_site.site.domain,
        )
        assert response.status_code == 200
        return response.content.decode("utf-8")

    response_text = get_response_text()
    expected = (
        f'{active_package_listing.get_wiki_url()}{page.full_slug}/">{page.title}</a>'
    )
    assert expected in response_text
    assert "<p>This wiki currently has no pages in it.</p>" not in response_text


@pytest.mark.django_db
def test_views_package_wiki_home_with_content(
    client,
    active_package_listing: PackageListing,
    community_site: CommunitySite,
    active_package_wiki_page: WikiPage,
) -> None:
    assert active_package_listing.package.has_wiki is True
    page = active_package_wiki_page

    def get_response_text():
        response = client.get(
            active_package_listing.get_wiki_url(),
            HTTP_HOST=community_site.site.domain,
        )
        assert response.status_code == 200
        return response.content.decode("utf-8")

    response_text = get_response_text()
    expected = (
        f'{active_package_listing.get_wiki_url()}{page.full_slug}/">{page.title}</a>'
    )
    assert expected in response_text
    assert "<p>This wiki currently has no pages in it.</p>" not in response_text


@pytest.mark.django_db
def test_views_package_wiki_page_detail(
    client,
    active_package_listing: PackageListing,
    community_site: CommunitySite,
    active_package_wiki_page: WikiPage,
) -> None:
    assert active_package_listing.package.has_wiki is True
    page = active_package_wiki_page

    def get_response_text():
        response = client.get(
            f"{active_package_listing.get_wiki_url()}{page.full_slug}/",
            HTTP_HOST=community_site.site.domain,
        )
        assert response.status_code == 200
        return response.content.decode("utf-8")

    expected_content = render_markdown(page.markdown_content)

    response_text = get_response_text()
    assert expected_content in response_text
    assert "Edit" not in response_text
    assert "New page" not in response_text

    team_user = UserFactory()
    TeamMemberFactory(team=active_package_listing.package.owner, user=team_user)
    client.force_login(team_user)

    response_text = get_response_text()
    assert expected_content in response_text
    assert "Edit" in response_text
    assert "New page" in response_text


@pytest.mark.django_db
def test_views_package_wiki_new_page(
    client,
    active_package_listing: PackageListing,
    community_site: CommunitySite,
) -> None:
    assert active_package_listing.package.has_wiki is False

    def get_response_text():
        response = client.get(
            f"{active_package_listing.get_wiki_url()}new/",
            HTTP_HOST=community_site.site.domain,
        )
        assert response.status_code == 200
        return response.content.decode("utf-8")

    response_text = get_response_text()
    assert "You don't have sufficient permissions to edit this wiki." in response_text
    assert extract_props_from_html(response_text, "PageEditPage", "edit-page") is None

    team_user = UserFactory()
    TeamMemberFactory(team=active_package_listing.package.owner, user=team_user)
    client.force_login(team_user)

    response_text = get_response_text()
    assert (
        extract_props_from_html(response_text, "PageEditPage", "edit-page") is not None
    )


@pytest.mark.django_db
def test_views_package_wiki_edit_page(
    client,
    active_package_listing: PackageListing,
    community_site: CommunitySite,
    active_package_wiki_page: WikiPage,
) -> None:
    assert active_package_listing.package.has_wiki is True
    page = active_package_wiki_page

    def get_response_text():
        response = client.get(
            f"{active_package_listing.get_wiki_url()}{page.full_slug}/edit/",
            HTTP_HOST=community_site.site.domain,
        )
        assert response.status_code == 200
        return response.content.decode("utf-8")

    response_text = get_response_text()
    assert "You don't have sufficient permissions to edit this wiki." in response_text
    assert extract_props_from_html(response_text, "PageEditPage", "edit-page") is None

    team_user = UserFactory()
    TeamMemberFactory(team=active_package_listing.package.owner, user=team_user)
    client.force_login(team_user)

    response_text = get_response_text()
    assert (
        extract_props_from_html(response_text, "PageEditPage", "edit-page") is not None
    )


@pytest.mark.django_db
def test_views_package_wiki_404(
    client,
    active_package_listing: PackageListing,
    community_site: CommunitySite,
) -> None:
    assert active_package_listing.package.has_wiki is False

    def get_response_text():
        response = client.get(
            f"{active_package_listing.get_wiki_url()}23-something/",
            HTTP_HOST=community_site.site.domain,
        )
        assert response.status_code == 404
        return response.content.decode("utf-8")

    response_text = get_response_text()
    assert "Looks like this wiki page doesn't exist" in response_text
    assert "Wiki page not found" in response_text


@pytest.mark.django_db
def test_views_package_wiki_slug_redirects(
    client,
    active_package_listing: PackageListing,
    community_site: CommunitySite,
    active_package_wiki_page: WikiPage,
) -> None:
    assert active_package_listing.package.has_wiki is True
    page = active_package_wiki_page

    def assert_redirect(path: str, redirect: bool):
        resp = client.get(
            f"{active_package_listing.get_wiki_url()}{path}/",
            HTTP_HOST=community_site.site.domain,
        )
        assert resp.status_code == 302 if redirect else 200
        if redirect:
            assert resp.url.endswith(
                f"{active_package_listing.get_wiki_url()}{page.full_slug}/"
            )

    assert_redirect(page.full_slug, False)
    assert_redirect(page.pk, True)
    assert_redirect(f"{page.pk}-", True)
    assert_redirect(f"{page.pk}-{page.full_slug}-foobar", True)
