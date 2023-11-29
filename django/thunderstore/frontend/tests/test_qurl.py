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
