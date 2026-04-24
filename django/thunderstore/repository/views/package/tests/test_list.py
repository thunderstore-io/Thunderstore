import pytest
from django.test import Client
from django.urls import reverse

from thunderstore.cache.enums import CacheBustCondition
from thunderstore.cache.tasks import invalidate_cache
from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.factories import (
    PackageCategoryFactory,
    PackageListingFactory,
)
from thunderstore.community.models import CommunitySite, PackageListing
from thunderstore.core.types import UserType
from thunderstore.repository.factories import PackageVersionFactory


@pytest.mark.django_db
def test_package_review_list_view(
    client: Client,
    active_package_listing: PackageListing,
    community_site: CommunitySite,
    user: UserType,
):
    active_package_listing.review_status = PackageListingReviewStatus.rejected
    active_package_listing.save()
    active_package_listing.request_review()

    invalidate_cache(cache_bust_condition=CacheBustCondition.any_package_updated)

    url = reverse("review-queue.packages")
    response = client.get(url, HTTP_HOST=community_site.site.domain)
    assert response.status_code == 403

    client.force_login(user)
    response = client.get(url, HTTP_HOST=community_site.site.domain)
    assert response.status_code == 403

    user.is_superuser = True
    user.save()

    response = client.get(url, HTTP_HOST=community_site.site.domain)
    assert response.status_code == 200
    assert active_package_listing.get_full_url().encode("utf-8") in response.content


@pytest.mark.django_db
def test_package_list_search_logic(
    client: Client,
    community_site: CommunitySite,
):
    url = reverse(
        "communities:community:packages.list",
        kwargs={
            "community_identifier": community_site.community.identifier,
        },
    )
    host = community_site.site.domain

    version = PackageVersionFactory(name="Fish_and_Birds")
    listing = PackageListingFactory(
        package=version.package, community=community_site.community
    )

    resp = client.get(f"{url}?q= ", HTTP_HOST=host)
    assert listing.get_full_url().encode("utf-8") in resp.content

    resp = client.get(f"{url}?q=fish", HTTP_HOST=host)
    assert listing.get_full_url().encode("utf-8") in resp.content

    resp = client.get(f"{url}?q=fish birds", HTTP_HOST=host)
    assert listing.get_full_url().encode("utf-8") in resp.content

    resp = client.get(f"{url}?q=fish cats", HTTP_HOST=host)
    assert listing.get_full_url().encode("utf-8") not in resp.content


@pytest.mark.django_db
def test_package_list_cache_vary_sanitization(community_site: CommunitySite):
    """
    Ensures that get_full_cache_vary strips poison payloads and
    normalizes parameter order.
    """
    from django.test import RequestFactory

    from thunderstore.repository.views.package.list import PackageListSearchView

    rf = RequestFactory()
    # A URL with unsorted params and cache poison (+payload)
    url = "/c/test/?deprecated=on+poison&q=search&page=1"
    request = rf.get(url)
    request.community = community_site.community

    view = PackageListSearchView()
    view.request = request
    view.kwargs = {}
    view.community = community_site.community

    cache_vary = view.get_full_cache_vary()

    assert "deprecated:on" in cache_vary
    assert "poison" not in cache_vary

    assert f"community:{community_site.community.identifier}" in cache_vary

    expected_order = (
        f"community:{community_site.community.identifier}."
        "type:."
        "deprecated:on."
        "ordering:last-updated."
        "page:1."
        "q:search"
    )
    assert cache_vary == expected_order


@pytest.mark.django_db
def test_package_list_category_filtering(
    client: Client,
    community_site: CommunitySite,
    active_package_listing: PackageListing,
):
    cat1 = PackageCategoryFactory()
    cat2 = PackageCategoryFactory()

    active_package_listing.categories.add(cat1)

    url = reverse(
        "communities:community:packages.list",
        kwargs={
            "community_identifier": community_site.community.identifier,
        },
    )

    resp = client.get(
        f"{url}?included_categories={cat1.pk}&included_categories={cat2.pk}",
        HTTP_HOST=community_site.site.domain,
    )
    assert resp.status_code == 200
    # Package has one of the included categories, search uses OR logic for categories
    assert active_package_listing.get_full_url().encode("utf-8") in resp.content

    resp = client.get(
        f"{url}?excluded_categories={cat1.pk}", HTTP_HOST=community_site.site.domain
    )
    assert resp.status_code == 200
    # Package has one of the excluded categories, search uses OR logic for categories
    assert active_package_listing.get_full_url().encode("utf-8") not in resp.content


@pytest.mark.django_db
def test_package_list_empty_category_params(
    client: Client,
    community_site: CommunitySite,
):
    url = reverse(
        "communities:community:packages.list",
        kwargs={
            "community_identifier": community_site.community.identifier,
        },
    )
    resp = client.get(
        f"{url}?included_categories=arbitrarystring",
        HTTP_HOST=community_site.site.domain,
    )
    assert resp.status_code == 200
