import pytest
from django.template import Context
from django.test import RequestFactory

from thunderstore.frontend.models import DynamicHTML, DynamicPlacement
from thunderstore.frontend.templatetags.dynamic_html import dynamic_html


@pytest.mark.django_db
def test_dynamic_html_returns_empty_string_without_get_dynamic_html():
    class DummyRequest:
        pass

    request = DummyRequest()
    context = Context({"request": request})

    DynamicHTML.objects.create(
        name="Dynamic HTML",
        content="I am content beginning",
        placement=DynamicPlacement.content_beginning,
    )

    assert not hasattr(request, "get_dynamic_html")
    assert "" == dynamic_html(context, placement=DynamicPlacement.content_beginning)
