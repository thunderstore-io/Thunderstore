from typing import List
from unittest.mock import Mock

import pytest
from django.http import HttpResponse
from django.test import RequestFactory

from thunderstore.account.factories import UserFlagFactory
from thunderstore.community.models import Community
from thunderstore.frontend.middleware import DynamicHTMLMiddleware
from thunderstore.frontend.models import DynamicHTML, DynamicPlacement


@pytest.mark.django_db
@pytest.mark.parametrize(
    "require_community, exclude_community, is_active, should_be_in_response",
    [
        (False, False, True, True),
        (True, False, True, True),
        (False, True, True, False),
        (True, True, True, False),
        (False, False, False, False),
    ],
)
def test_dynamic_html_middleware(
    rf: RequestFactory,
    community: Community,
    require_community,
    exclude_community,
    is_active,
    should_be_in_response,
):
    request = rf.get("/")
    request.community = community

    dhtml = DynamicHTML.objects.create(
        name="Dynamic HTML 1",
        content="Dynamic HTML content here",
        placement=DynamicPlacement.content_beginning,
    )
    if require_community:
        dhtml.require_communities.add(community)
    if exclude_community:
        dhtml.exclude_communities.add(community)
    if not is_active:
        dhtml.is_active = False
    dhtml.save()

    def dummy_view(request):
        html = request.get_dynamic_html()
        return HttpResponse(str(html))

    middleware = DynamicHTMLMiddleware(get_response=dummy_view)
    middleware.process_view(request, dummy_view, [], {})
    response = middleware(request)

    assert response.status_code == 200
    if should_be_in_response:
        assert dhtml.content in response.content.decode()
    else:
        assert dhtml.content not in response.content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("required_flags", "excluded_flags", "user_flags", "should_be_in_response"),
    (
        ([], [], [], True),
        ([], [], ["flag-1"], True),
        (["flag-1"], [], [], False),
        (["flag-1"], [], ["flag-1"], True),
        (["flag-1"], [], ["flag-1", "flag-2"], True),
        ([], ["flag-2"], [], True),
        ([], ["flag-2"], ["flag-2"], False),
        ([], ["flag-2"], ["flag-1", "flag-2"], False),
        (["flag-1"], ["flag-2"], ["flag-1"], True),
        (["flag-1"], ["flag-1", "flag-2"], ["flag-1"], False),
        (["flag-1", "flag-2"], [], ["flag-2"], True),
    ),
)
def test_dynamic_html_middleware_user_flag_filtering(
    rf: RequestFactory,
    community: Community,
    required_flags: List[str],
    excluded_flags: List[str],
    user_flags: List[str],
    should_be_in_response: bool,
):
    request = rf.get("/")
    request.community = community
    request.get_user_flags = Mock(return_value=user_flags)

    flag_ids = set().union((*required_flags, *excluded_flags))
    flags = {}

    for flag_id in flag_ids:
        flags[flag_id] = UserFlagFactory(identifier=flag_id)

    dhtml = DynamicHTML.objects.create(
        name="Test HTML",
        content="Dynamic HTML content here",
        placement=DynamicPlacement.content_beginning,
    )
    dhtml.exclude_user_flags.set([flags[x] for x in excluded_flags])
    dhtml.require_user_flags.set([flags[x] for x in required_flags])

    def dummy_view(request):
        html = request.get_dynamic_html()
        return HttpResponse(str(html))

    middleware = DynamicHTMLMiddleware(get_response=dummy_view)
    middleware.process_view(request, dummy_view, [], {})
    response = middleware(request)

    if should_be_in_response:
        assert dhtml.content in response.content.decode()
    else:
        assert dhtml.content not in response.content.decode()


@pytest.mark.django_db
def test_dynamic_html_middleware_multiple_objects(
    rf: RequestFactory,
    community: Community,
):
    request = rf.get("/")
    request.community = community

    dhtml1 = DynamicHTML.objects.create(
        name="Dynamic HTML 1",
        content="Dynamic HTML content 1",
        placement=DynamicPlacement.content_beginning,
    )
    dhtml2 = DynamicHTML.objects.create(
        name="Dynamic HTML 2",
        content="Dynamic HTML content 2",
        placement=DynamicPlacement.content_beginning,
    )
    dhtml3 = DynamicHTML.objects.create(
        name="Dynamic HTML 2",
        content="Dynamic HTML content 3",
        placement=DynamicPlacement.content_end,
    )

    def dummy_view(request):
        html = request.get_dynamic_html()
        return HttpResponse(str(html))

    middleware = DynamicHTMLMiddleware(get_response=dummy_view)
    middleware.process_view(request, dummy_view, [], {})
    response = middleware(request)

    assert response.status_code == 200
    assert dhtml1.content in response.content.decode()
    assert dhtml2.content in response.content.decode()
    assert dhtml3.content in response.content.decode()


@pytest.mark.django_db
def test_middleware_get_dynamic_html_is_cached(
    mocker, rf: RequestFactory, community: Community
):
    request = rf.get("/")
    request.community = community

    spy = mocker.spy(DynamicHTML._default_manager, "filter")

    assert spy.call_count == 0

    DynamicHTML.objects.create(
        name="Dynamic HTML 1",
        content="I am cached",
        placement=DynamicPlacement.content_beginning,
    )

    def dummy_view(request):
        html = request.get_dynamic_html()
        return HttpResponse(str(html))

    middleware = DynamicHTMLMiddleware(get_response=dummy_view)
    middleware.process_view(request, dummy_view, [], {})
    middleware(request)

    assert spy.call_count == 1

    assert hasattr(request, "get_dynamic_html")
    assert "I am cached" in str(request.get_dynamic_html())
    [request.get_dynamic_html() for _ in range(3)]
    assert spy.call_count == 1


@pytest.mark.django_db
def test_middleware_get_dynamic_html_with_no_content(rf: RequestFactory):
    request = rf.get("/")
    request.community = None

    DynamicHTML.objects.create(
        name="Dynamic HTML 1",
        placement=DynamicPlacement.content_beginning,
    )

    def dummy_view(request):
        html = request.get_dynamic_html()
        return HttpResponse(str(html))

    middleware = DynamicHTMLMiddleware(get_response=dummy_view)
    middleware.process_view(request, dummy_view, [], {})
    middleware(request)

    assert hasattr(request, "get_dynamic_html")
    assert "{}" == str(request.get_dynamic_html())
