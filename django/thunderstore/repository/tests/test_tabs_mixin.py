import pytest

from thunderstore.community.models import PackageListing
from thunderstore.core.factories import UserFactory
from thunderstore.core.types import UserType
from thunderstore.repository.factories import PackageWikiFactory, TeamMemberFactory
from thunderstore.repository.views.mixins import PackageTabsMixin
from thunderstore.wiki.factories import WikiPageFactory

KNOWN_TABS = ("details", "versions", "changelog", "wiki")


@pytest.mark.django_db
@pytest.mark.parametrize("active_tab", KNOWN_TABS)
def test_get_tab_context(
    user: UserType,
    active_package_listing: PackageListing,
    active_tab: str,
) -> None:
    tabs_mixin = PackageTabsMixin()
    context = tabs_mixin.get_tab_context(
        user,
        active_package_listing,
        active_tab,
    )
    tabs = context["tabs"]

    assert tabs[0].name == "details"
    assert tabs[0].url == active_package_listing.get_absolute_url()
    assert tabs[0].is_disabled is False

    assert tabs[1].name == "versions"
    assert tabs[1].url == active_package_listing.get_versions_url()
    assert tabs[1].is_disabled is False

    assert tabs[2].name == "changelog"
    assert tabs[2].url == active_package_listing.get_changelog_url()
    assert tabs[2].is_disabled is (active_tab != "changelog")

    assert tabs[3].name == "wiki"
    assert tabs[3].url == active_package_listing.get_wiki_url()
    assert tabs[3].is_disabled is (active_tab != "wiki")

    for tab in tabs:
        assert tab.is_active is (tab.name == active_tab)


@pytest.mark.django_db
def test_get_tab_context_wiki_disabled(
    user: UserType,
    active_package_listing: PackageListing,
) -> None:
    team_user = UserFactory()
    TeamMemberFactory(team=active_package_listing.package.owner, user=team_user)

    tabs_mixin = PackageTabsMixin()

    def assert_disabled(user: UserType, expected: bool) -> None:
        tabs = tabs_mixin.get_tab_context(
            user,
            active_package_listing,
            "details",
        )["tabs"]
        assert tabs[3].name == "wiki"
        assert tabs[3].is_disabled is expected

    assert_disabled(user, True)
    assert_disabled(team_user, False)

    package_wiki = PackageWikiFactory(package=active_package_listing.package)
    del active_package_listing.package.has_wiki
    assert_disabled(user, True)
    assert_disabled(team_user, False)
    WikiPageFactory(wiki=package_wiki.wiki)
    del active_package_listing.package.has_wiki
    assert_disabled(user, False)
    assert_disabled(team_user, False)


@pytest.mark.django_db
def test_get_tab_context_changelog_disabled(
    user: UserType,
    active_package_listing: PackageListing,
) -> None:
    tabs_mixin = PackageTabsMixin()

    def assert_disabled(user: UserType, expected: bool) -> None:
        tabs = tabs_mixin.get_tab_context(
            user,
            active_package_listing,
            "details",
        )["tabs"]
        assert tabs[2].name == "changelog"
        assert tabs[2].is_disabled is expected

    assert_disabled(user, True)

    active_package_listing.package.latest.changelog = "# Foo bar"
    active_package_listing.package.latest.save()
    assert_disabled(user, False)


@pytest.mark.django_db
def test_active_tabs_are_visible(
    user: UserType,
    active_package_listing: PackageListing,
) -> None:
    tabs_mixin = PackageTabsMixin()

    tabs1 = tabs_mixin.get_tab_context(
        user,
        active_package_listing,
        "details",
    )["tabs"]

    for tab1 in tabs1:
        tabs2 = tabs_mixin.get_tab_context(
            user,
            active_package_listing,
            tab1.name,
        )["tabs"]

        for tab2 in tabs2:
            if tab2.is_active:
                assert tab2.is_visible
