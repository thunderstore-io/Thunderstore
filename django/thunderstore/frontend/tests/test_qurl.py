from io import BytesIO

import pytest
from django.test import RequestFactory
from django.urls import reverse
from lxml import etree
from rest_framework.test import APIClient

from thunderstore.community.factories import PackageListingFactory
from thunderstore.community.models import CommunitySite, PackageListingSection
from thunderstore.frontend.templatetags.qurl import QurlNode

TEST_PARAMS = (
    ("page", True),
    ("q", True),
    ("included_categories", True),
    ("excluded_categories", True),
    ("nsfw", True),
    ("deprecated", True),
    ("ordering", True),
    ("section", True),
    ("foo", False),
    ("jwoejfiwejof", False),
)


@pytest.mark.django_db
@pytest.mark.parametrize(("param", "should_exist"), TEST_PARAMS)
def test_qurl_parameter_filtering_package_listing_view(
    client: APIClient,
    community_site: CommunitySite,
    param: str,
    should_exist: bool,
) -> None:
    # Param has to be a valid value or it won't be rendered
    param_val = "foo"

    # Section select needs to exist -> create enough sections
    for i in range(2):
        slug = f"section-{i}"
        PackageListingSection.objects.create(
            community=community_site.community,
            name=f"Section {i}",
            slug=slug,
        )
        param_val = slug

    # Pagination has to exist -> create enough packages
    if param == "page":
        for i in range(25):
            PackageListingFactory(community=community_site.community)
        param_val = "1"

    response = client.get(
        reverse(
            "communities:community:packages.list",
            kwargs={"community_identifier": community_site.community.identifier},
        )
        + f"?{param}={param_val}",
        HTTP_HOST=community_site.site.domain,
    )

    buffer = BytesIO(response.content)
    tree = etree.parse(buffer, etree.HTMLParser())

    param_found = False
    for entry in tree.findall(".//a"):
        href = entry.get("href", "")
        if param in href and "/auth/login" not in href:
            param_found = True
            break

    if should_exist:
        assert param_found is True
    else:
        assert param_found is False


@pytest.mark.django_db
@pytest.mark.parametrize(("param", "should_exist"), TEST_PARAMS)
def test_qurl_parameter_filtering_static(
    rf: RequestFactory,
    community_site: CommunitySite,
    param: str,
    should_exist: bool,
) -> None:
    url = (
        reverse(
            "communities:community:packages.list",
            kwargs={"community_identifier": community_site.community.identifier},
        )
        + f"?{param}=1"
    )
    context = {
        "allowed_params": {
            "q",
            "ordering",
            "deprecated",
            "nsfw",
            "excluded_categories",
            "included_categories",
            "section",
            "page",
        },
        "request": rf.get(url),
    }

    class FilterStub:
        def resolve(self, context):
            return "noop"

    qurl = QurlNode("allowed_params", "noop", FilterStub(), [])
    result = qurl.render(context)
    if should_exist:
        assert param in result
    else:
        assert param not in result


ALLOWED_LIST_PARAMS = {
    "q",
    "ordering",
    "deprecated",
    "nsfw",
    "excluded_categories",
    "included_categories",
    "section",
    "page",
}


class _FilterStub:
    def __init__(self, value: str = "1") -> None:
        self.value = value

    def resolve(self, context):  # noqa: ARG002
        return self.value


def _int_validator(value: str):
    return str(int(value))


def _ordering_validator(value: str):
    return value if value in {"newest", "last-updated"} else None


def _page_validator(value: str):
    number = int(value)
    return str(number) if 1 <= number <= 10_000 else None


POISONED_VALUES = [
    "5'\\\"\u00a7ion=modpacks\u00a7ion=seekers-of-the-storm",
    "<script>alert(1)</script>",
    "1\r\nSet-Cookie: injected=1",
    "a" * 1000,
    "../../etc/passwd",
]


@pytest.mark.parametrize("value", POISONED_VALUES)
def test_qurl_drops_unvalidated_garbage_values(
    rf: RequestFactory, value: str
) -> None:
    request = rf.get(
        "/", {"included_categories": value, "ordering": "newest"}
    )
    context = {
        "request": request,
        "allowed_params": ALLOWED_LIST_PARAMS,
        "allowed_params_validators": {
            "included_categories": _int_validator,
            "ordering": _ordering_validator,
            "page": _page_validator,
        },
    }
    result = QurlNode("allowed_params", "page", _FilterStub("2"), []).render(context)

    assert "included_categories" not in result
    assert "\u00a7" not in result
    assert "script" not in result
    assert "Set-Cookie" not in result
    assert "ordering=newest" in result
    assert "page=2" in result


def test_qurl_preserves_validated_duplicate_values(rf: RequestFactory) -> None:
    request = rf.get(
        "/?included_categories=1&included_categories=2&included_categories=abc"
    )
    context = {
        "request": request,
        "allowed_params": ALLOWED_LIST_PARAMS,
        "allowed_params_validators": {
            "included_categories": _int_validator,
        },
    }
    result = QurlNode("allowed_params", "page", _FilterStub("3"), []).render(context)

    assert "included_categories=1" in result
    assert "included_categories=2" in result
    assert "abc" not in result
    assert "page=3" in result


def test_qurl_default_filter_blocks_control_characters(rf: RequestFactory) -> None:
    request = rf.get("/?q=hello\x00\x1fworld&ordering=newest")
    context = {
        "request": request,
        "allowed_params": {"q", "ordering", "page"},
    }
    result = QurlNode("allowed_params", "page", _FilterStub("1"), []).render(context)

    assert "\x00" not in result
    assert "\x1f" not in result
    assert "q=helloworld" in result


def test_qurl_default_filter_blocks_excessively_long_values(
    rf: RequestFactory,
) -> None:
    request = rf.get("/", {"q": "a" * 1000, "ordering": "newest"})
    context = {
        "request": request,
        "allowed_params": {"q", "ordering", "page"},
    }
    result = QurlNode("allowed_params", "page", _FilterStub("1"), []).render(context)

    assert "q=" not in result
    assert "ordering=newest" in result


def test_qurl_does_not_reflect_path_from_request(rf: RequestFactory) -> None:
    # Regression: the emitted href must use the request's current path,
    # not whatever Referer or Host a bot supplies.
    request = rf.get("/c/riskofrain2/?ordering=newest")
    context = {
        "request": request,
        "allowed_params": {"ordering", "page"},
        "allowed_params_validators": {
            "ordering": _ordering_validator,
            "page": _page_validator,
        },
    }
    result = QurlNode("allowed_params", "page", _FilterStub("2"), []).render(context)

    assert result.startswith("/c/riskofrain2/?")
