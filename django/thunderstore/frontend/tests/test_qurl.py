import pytest
from django.template import Context, Template
from django.test import RequestFactory

ALLOWED_PARAMS = [
    "q",
    "ordering",
    "deprecated",
    "nsfw",
    "excluded_categories",
    "included_categories",
    "section",
    "page",
]


class MockView:
    """Simulates the PackageListSearchView behavior."""

    def __init__(self, request, params):
        self.request = request
        self.params = params

    def get_clean_params(self):
        return {k: v for k, v in self.params.items() if k in ALLOWED_PARAMS}


@pytest.mark.django_db
def test_qurl_simple_tag_logic(rf: RequestFactory):
    """Verifies that qurl updates one param while keeping others and dropping 'foo'."""
    url = "/c/test/?q=search&foo=bar&page=1"
    request = rf.get(url)

    # Simulate the sanitized dict that get_clean_params would return
    clean_params = {"q": "search", "page": "1"}
    view = MockView(request, clean_params)

    context = Context(
        {
            "view": view,
            "request": request,
        }
    )

    # Test updating page from 1 to 2
    template = Template("{% load qurl %}{% qurl 'page' 2 %}")
    result = template.render(context)

    assert "page=2" in result
    assert "q=search" in result
    assert "foo" not in result  # Dropped because it's not in clean_params
    assert result.startswith("/c/test/")


@pytest.mark.django_db
def test_qurl_handles_lists(rf: RequestFactory):
    """Ensures category lists are encoded correctly (doseq=True)."""
    clean_params = {"included_categories": [1, 2]}
    request = rf.get("/c/test/")
    view = MockView(request, clean_params)

    context = Context({"view": view, "request": request})
    template = Template("{% load qurl %}{% qurl 'page' 1 %}")
    result = template.render(context)

    assert "included_categories=1" in result
    assert "included_categories=2" in result
    assert "page=1" in result


@pytest.mark.django_db
def test_qurl_missing_view(rf: RequestFactory):
    """The tag should return an empty string if the view is missing/invalid."""
    context = Context({"request": rf.get("/")})  # No 'view' in context
    template = Template("{% load qurl %}{% qurl 'page' 1 %}")
    result = template.render(context)

    assert result == ""
