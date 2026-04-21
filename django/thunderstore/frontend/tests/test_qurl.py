import pytest
from django.test import RequestFactory

from thunderstore.frontend.templatetags.qurl import QurlNode


class _FilterStub:
    def __init__(self, value: str = "1") -> None:
        self.value = value

    def resolve(self, context):
        return self.value


@pytest.mark.parametrize(
    "param_to_change, new_value, expected_substring",
    [
        ("page", "2", "page=2"),
        ("section", "mods", "section=mods"),
        ("ordering", "newest", "ordering=newest"),
    ],
)
def test_qurl_uses_context_variables_and_updates_active_param(
    rf: RequestFactory, param_to_change, new_value, expected_substring
) -> None:
    """
    Ensures qurl pulls from context mapping (e.g., active_ordering)
    and prioritizes the param_val passed in the tag.
    """
    request = rf.get("/c/riskofrain2/")
    context = {
        "request": request,
        "allowed_params": {"q", "ordering", "section", "page"},
        "current_search": "test-search",
        "active_ordering": "last-updated",
        "active_section": "all",
        "page_number": "1",
    }

    # If we are changing 'ordering' to 'newest', the final URL should have newest
    # but still keep the 'test-search' from current_search context variable.
    node = QurlNode("allowed_params", param_to_change, _FilterStub(new_value), [])
    result = node.render(context)

    assert expected_substring in result
    assert "q=test-search" in result
    if param_to_change != "ordering":
        assert "ordering=last-updated" in result


def test_qurl_sanitizes_list_types_from_context(rf: RequestFactory) -> None:
    """
    Ensures included_categories (list/set in context) are sorted and joined correctly.
    """
    request = rf.get("/")
    context = {
        "request": request,
        "allowed_params": {"included_categories", "page"},
        "included_categories": [10, 5, 2],  # Out of order
        "page_number": "1",
    }

    node = QurlNode("allowed_params", "page", _FilterStub("2"), [])
    result = node.render(context)

    # Should be sorted: 2, 5, 10
    assert (
        "included_categories=2&included_categories=5&included_categories=10" in result
    )
    assert "page=2" in result


def test_qurl_handles_boolean_on_state(rf: RequestFactory) -> None:
    """
    Ensures True/False in context becomes 'on' or dropped in the URL.
    """
    request = rf.get("/")
    context = {
        "request": request,
        "allowed_params": {"nsfw", "deprecated", "page"},
        "nsfw_included": True,
        "deprecated_included": False,
        "page_number": "1",
    }

    node = QurlNode("allowed_params", "page", _FilterStub("1"), [])
    result = node.render(context)

    assert "nsfw=on" in result
    assert "deprecated=" not in result


def test_qurl_removals_work_on_context_keys(rf: RequestFactory) -> None:
    """
    Ensures the removals argument (comma separated) drops keys from the final URL.
    """
    request = rf.get("/")
    context = {
        "request": request,
        "allowed_params": {"q", "ordering", "page"},
        "current_search": "find-me",
        "active_ordering": "newest",
    }

    # Tag: {% qurl allowed_params page 1 q %} -> removes 'q'
    node = QurlNode("allowed_params", "page", _FilterStub("1"), ["q"])
    result = node.render(context)

    assert "ordering=newest" in result
    assert "q=" not in result
