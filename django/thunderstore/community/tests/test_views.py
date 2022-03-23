from collections import Counter
from urllib.request import Request

import pytest
from django.contrib.sites.models import Site
from django.db.models import Q
from django.http import QueryDict

from thunderstore.community.models.community import Community
from thunderstore.community.models.community_site import CommunitySite
from thunderstore.community.views.community import CommunitiesView


@pytest.mark.django_db
def test_package_detail_view(client, active_package_listing, community_site):
    package = active_package_listing.package
    response = client.get(
        active_package_listing.get_absolute_url(),
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 200
    text_result = response.content.decode("utf-8")
    assert package.name in text_result
    assert package.full_package_name in text_result


@pytest.mark.django_db
def test_package_dependants_view(client, active_package_listing, community_site):
    response = client.get(
        active_package_listing.dependants_url, HTTP_HOST=community_site.site.domain
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_communities_view_get_base_queryset(community_site):
    CommunitySite.objects.create(
        site=Site.objects.create(domain="notlisted.testsite.test", name="NotListed"),
        community=Community.objects.create(name="Not Listed", identifier="notlisted"),
        is_listed=False,
    )
    assert Counter(CommunitiesView().get_base_queryset()) == Counter(
        CommunitySite.objects.exclude(is_listed=False)
    )


@pytest.mark.django_db
def test_communities_view_get_page_title(community_site):
    assert CommunitiesView().get_page_title() == "Communities"


@pytest.mark.django_db
def test_communities_view_get_cache_vary(community_site):
    assert CommunitiesView().get_cache_vary() == "communities"


@pytest.mark.django_db
def test_communities_view_get_search_query(community_site):
    view = CommunitiesView()
    view.request = Request(url="http://testsite.test/communities/")
    view.request.GET = QueryDict("q=test")
    assert view.get_search_query() == "test"


@pytest.mark.django_db
def test_communities_view_get_full_cache_vary(community_site):
    view = CommunitiesView()
    view.request = Request(url="http://testsite.test/communities/")
    view.request.GET = QueryDict("q=test")
    assert view.get_full_cache_vary() == (view.get_cache_vary() + ".test")


@pytest.mark.django_db
def test_communities_view_order_queryset(community_site):
    view = CommunitiesView()
    CommunitySite.objects.create(
        site=Site.objects.create(domain="xcom.testsite.test", name="X Com"),
        community=Community.objects.create(name="X Com", identifier="xcom"),
    )
    assert Counter(
        CommunitiesView().order_queryset(queryset=view.get_base_queryset())
    ) == Counter(
        CommunitySite.objects.exclude(is_listed=False).order_by("community__name")
    )


@pytest.mark.django_db
def test_communities_view_perform_search(community_site):
    CommunitySite.objects.create(
        site=Site.objects.create(domain="xcom.testsite.test", name="X Com"),
        community=Community.objects.create(name="X Com", identifier="xcom"),
    )
    view = CommunitiesView()
    view.request = Request(url="http://testsite.test/communities/")
    view.request.GET = QueryDict("q=test")
    assert Counter(
        view.perform_search(
            queryset=view.get_base_queryset(), search_query=view.get_search_query()
        )
    ) == Counter(
        CommunitySite.objects.filter(community__name__icontains="test").distinct()
    )


@pytest.mark.django_db
def test_communities_view_get_queryset(community_site):
    CommunitySite.objects.create(
        site=Site.objects.create(domain="xcom.testsite.test", name="X Com"),
        community=Community.objects.create(name="X Com", identifier="xcom"),
    )
    view = CommunitiesView()
    view.request = Request(url="http://testsite.test/communities/")
    view.request.GET = QueryDict("q=test")
    assert Counter(view.get_queryset()) == Counter(
        CommunitySite.objects.filter(
            Q(Q(community__name="test") | Q(community__identifier="test")),
            is_listed=True,
        )
        .distinct()
        .order_by("community__name")
    )


@pytest.mark.django_db
def test_communities_view_get_paginator(community_site):
    CommunitySite.objects.create(
        site=Site.objects.create(domain="xcom.testsite.test", name="X Com"),
        community=Community.objects.create(name="X Com", identifier="xcom"),
    )
    view = CommunitiesView()
    view.request = Request(url="http://testsite.test/communities/")
    view.request.GET = QueryDict("q=test")
    assert view.get_paginator(
        view.get_queryset(),
        1,
        orphans=0,
        allow_empty_first_page=True,
    )


@pytest.mark.django_db
def test_communities_view_get_context_data(community_site):
    CommunitySite.objects.create(
        site=Site.objects.create(domain="xcom.testsite.test", name="X Com"),
        community=Community.objects.create(name="X Com", identifier="xcom"),
    )
    view = CommunitiesView()
    view.kwargs = {}
    view.request = Request(url="http://testsite.test/communities/")
    view.request.GET = QueryDict("q=test")
    view.object_list = view.get_queryset()
    context = super(CommunitiesView, view).get_context_data()
    context["cache_vary"] = view.get_full_cache_vary()
    context["page_title"] = view.get_page_title()
    context["current_search"] = view.get_search_query()
    view_context_data = view.get_context_data()
    assert context["cache_vary"] == view_context_data["cache_vary"]
    assert context["page_title"] == view_context_data["page_title"]
    assert context["current_search"] == view_context_data["current_search"]
