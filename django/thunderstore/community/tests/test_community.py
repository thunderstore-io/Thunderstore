import pytest
from django.core.exceptions import ValidationError
from django.db.models import Prefetch

from conftest import TestUserTypes
from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.factories import CommunityFactory, CommunitySiteFactory
from thunderstore.community.models import (
    Community,
    CommunityMemberRole,
    CommunityMembership,
)
from thunderstore.community.models.community import get_community_filepath
from thunderstore.community.models.community_site import CommunitySite


@pytest.mark.django_db
def test_community_manager_listed():
    c1 = CommunityFactory(is_listed=True)
    c2 = CommunityFactory(is_listed=False)

    listed_communities = Community.objects.listed()
    assert c1 in listed_communities
    assert c2 not in listed_communities


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
@pytest.mark.parametrize("role", CommunityMemberRole.options() + [None])
def test_community_ensure_user_can_manage_packages(
    community: Community,
    user_type: str,
    role: str,
):
    user = TestUserTypes.get_user_by_type(user_type)
    if role is not None and user_type not in TestUserTypes.fake_users():
        CommunityMembership.objects.create(
            user=user,
            community=community,
            role=role,
        )

    result = community.can_user_manage_packages(user)
    error = None
    try:
        community.ensure_user_can_moderate_packages(user)
    except ValidationError as e:
        error = str(e)

    if user_type in TestUserTypes.fake_users():
        assert result is False
        assert "Must be authenticated" in error
        return
    elif user_type == TestUserTypes.deactivated_user:
        assert result is False
        assert "User has been deactivated" in error
    elif user_type == TestUserTypes.service_account:
        assert result is False
        assert "Service accounts are unable to perform this action" in error
    elif role not in (
        CommunityMemberRole.moderator,
        CommunityMemberRole.owner,
    ) and not (user.is_superuser or user.is_staff):
        assert result is False
        assert "Must be a moderator or higher to manage packages" in error
    else:
        assert result is True
        assert error is None


@pytest.mark.django_db
def test_community_image_url_without_image():
    community = CommunityFactory()
    url = community.community_icon_url
    assert url is None


@pytest.mark.django_db
def test_community_image_url_with_image(dummy_image):
    community = CommunityFactory(community_icon=dummy_image)
    url = community.community_icon_url
    assert isinstance(url, str)


@pytest.mark.django_db
def test_background_image_url_when_community_has_no_image():
    community = CommunityFactory()
    url = community.background_image_url
    assert url is None


@pytest.mark.django_db
def test_background_image_url_when_community_has_image(dummy_image):
    community = CommunityFactory(background_image=dummy_image)
    url = community.background_image_url
    assert isinstance(url, str)
    assert len(url) > 0


@pytest.mark.django_db
def test_hero_image_url_when_community_has_no_image():
    community = CommunityFactory()
    url = community.hero_image_url
    assert url is None


@pytest.mark.django_db
def test_hero_image_url_when_community_has_image(dummy_hero_image):
    community = CommunityFactory(hero_image=dummy_hero_image)
    url = community.hero_image_url
    assert isinstance(url, str)
    assert len(url) > 0


@pytest.mark.django_db
def test_cover_image_url_when_community_has_no_image():
    community = CommunityFactory()
    url = community.cover_image_url
    assert url is None


@pytest.mark.django_db
def test_cover_image_url_when_community_has_image(dummy_image):
    community = CommunityFactory(cover_image=dummy_image)
    url = community.cover_image_url
    assert isinstance(url, str)
    assert len(url) > 0


@pytest.mark.django_db
def test_icon_url_when_community_has_no_image():
    community = CommunityFactory()
    url = community.icon_url
    assert url is None


@pytest.mark.django_db
def test_icon_url_when_community_has_image(dummy_image):
    community = CommunityFactory(icon=dummy_image)
    url = community.icon_url
    assert isinstance(url, str)
    assert len(url) > 0


@pytest.mark.django_db
def test_image_url_logic_priority_path_and_host(settings, dummy_image):
    settings.COMMUNITY_IMAGE_HOST = "https://gcdn.thunderstore.io/"
    community = CommunityFactory(icon_path="/icons/test.png", icon=dummy_image)
    assert community.icon_url == "https://gcdn.thunderstore.io/icons/test.png"


@pytest.mark.django_db
def test_image_url_logic_priority_no_path(settings, dummy_image):
    settings.COMMUNITY_IMAGE_HOST = "https://gcdn.thunderstore.io/"
    community_no_path = CommunityFactory(icon_path=None, icon=dummy_image)
    assert community_no_path.icon_url == community_no_path.icon.url


@pytest.mark.django_db
def test_image_url_logic_priority_no_host(settings, dummy_image):
    settings.COMMUNITY_IMAGE_HOST = ""
    community = CommunityFactory(icon_path="/icons/test.png", icon=dummy_image)
    assert community.icon_url == community.icon.url


@pytest.mark.django_db
def test_community_site_get_absolute_url(community_site: CommunitySite) -> None:
    assert community_site.get_absolute_url == "/c/test/"


@pytest.mark.django_db
def test_community_get_community_filepath(community: Community) -> None:
    assert (
        get_community_filepath(community, "lol.png")
        == f"community/{community.identifier}/lol.png"
    )


@pytest.mark.django_db
@pytest.mark.parametrize("require_approval", (False, True))
def test_community_valid_review_statuses(
    community: Community,
    require_approval: bool,
) -> None:
    community.require_package_listing_approval = require_approval
    community.save()
    if require_approval:
        assert community.valid_review_statuses == (PackageListingReviewStatus.approved,)
    else:
        assert community.valid_review_statuses == (
            PackageListingReviewStatus.approved,
            PackageListingReviewStatus.unreviewed,
        )


@pytest.mark.django_db
@pytest.mark.parametrize("has_site", (False, True))
def test_community_full_url(
    community: Community,
    has_site: bool,
) -> None:
    if has_site:
        site = CommunitySiteFactory(community=community)
        expected = site.full_url
    else:
        expected = f"/c/{community.identifier}/"
    assert community.full_url == expected


@pytest.mark.django_db
@pytest.mark.parametrize("has_site", (False, True))
def test_community_get_absolute_url(
    community: Community,
    has_site: bool,
) -> None:
    # get_absolute_url is always the host-relative path, regardless of whether
    # the community has a main_site, so in-site navigation stays on the host
    # that served the page (e.g. the legacy old. site).
    if has_site:
        CommunitySiteFactory(community=community)
    assert community.get_absolute_url() == f"/c/{community.identifier}/"


@pytest.mark.django_db
@pytest.mark.parametrize("primary_created_first", (True, False))
def test_community_main_site_prefers_primary_host(
    community: Community,
    primary_created_first: bool,
    settings,
) -> None:
    # main_site must deterministically resolve to the PRIMARY_HOST site even when
    # the community is also bound to the legacy `old.` mirror host, so absolute
    # URLs built from it (the v1 API package_url, full_url, …) never drift to old.
    settings.PRIMARY_HOST = "primary.example.localhost"
    domains = ["primary.example.localhost", "legacy.example.localhost"]
    if not primary_created_first:
        domains.reverse()
    for domain in domains:
        CommunitySiteFactory(community=community, site__domain=domain)

    # Reload so main_site (a cached_property) is computed against the new sites.
    community = Community.objects.get(pk=community.pk)

    assert community.main_site.site.domain == "primary.example.localhost"
    assert "primary.example.localhost" in community.full_url
    assert "legacy.example.localhost" not in community.full_url


@pytest.mark.django_db
def test_community_main_site_does_not_n_plus_one(
    community: Community,
    django_assert_num_queries,
    settings,
) -> None:
    settings.PRIMARY_HOST = "primary.example.localhost"
    for domain in (
        "legacy.example.localhost",
        "other.example.localhost",
        "primary.example.localhost",
    ):
        CommunitySiteFactory(community=community, site__domain=domain)

    # Not prefetched: a single select_related query must resolve every site and
    # its domain — the per-site comparison must not add a query per row.
    fresh = Community.objects.get(pk=community.pk)
    with django_assert_num_queries(1):
        assert fresh.main_site.site.domain == "primary.example.localhost"

    # Prefetched the way CommunityMixin loads it: main_site must hit no queries.
    prefetched = Community.objects.prefetch_related(
        Prefetch("sites", queryset=CommunitySite.objects.select_related("site"))
    ).get(pk=community.pk)
    with django_assert_num_queries(0):
        assert prefetched.main_site.site.domain == "primary.example.localhost"


@pytest.mark.django_db
@pytest.mark.parametrize("has_site", (False, True))
def test_community_should_use_old_urls(
    community: Community,
    has_site: bool,
) -> None:
    if has_site:
        CommunitySiteFactory(community=community)
        expected = True
    else:
        expected = False
    assert Community.should_use_old_urls(community) is expected


def test_community_should_use_old_urls_no_community() -> None:
    assert Community.should_use_old_urls(None) is True


@pytest.mark.django_db
def test_community_validate_identifier_on_save():
    community = CommunityFactory()
    community.identifier = "test"
    with pytest.raises(ValidationError):
        community.save()
