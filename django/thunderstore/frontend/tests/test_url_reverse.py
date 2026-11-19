import pytest
from django.urls import URLPattern, reverse

from thunderstore.community.consts import DEFAULT_COMMUNITY_IDENTIFIER
from thunderstore.community.factories import CommunityFactory, CommunitySiteFactory
from thunderstore.frontend.tests.utils import get_url_kwarg
from thunderstore.frontend.url_reverse import get_community_url_reverse_args
from thunderstore.repository.urls import package_urls


@pytest.mark.django_db
@pytest.mark.parametrize("url_pattern", [x for x in package_urls if hasattr(x, "name")])
@pytest.mark.parametrize(
    ("identifier", "with_site", "uses_old_urls"),
    (
        (DEFAULT_COMMUNITY_IDENTIFIER, True, True),
        (DEFAULT_COMMUNITY_IDENTIFIER, False, False),
        ("test", True, False),
        ("test", False, False),
    ),
)
def test_get_community_url_reverse_args(
    url_pattern: URLPattern,
    identifier: str,
    with_site: bool,
    uses_old_urls: bool,
) -> None:
    community = CommunityFactory(identifier=identifier)

    required_kwargs = {
        k: get_url_kwarg(k) for k in url_pattern.pattern.regex.groupindex.keys()
    }
    required_kwargs = required_kwargs if required_kwargs else None

    if with_site:
        CommunitySiteFactory(community=community)

    if uses_old_urls:
        expected_kwargs = required_kwargs
        expected_prefix = "old_urls:"
    else:
        expected_kwargs = {
            **(required_kwargs or {}),
            **{"community_identifier": community.identifier},
        }
        expected_prefix = "communities:community:"

    result = get_community_url_reverse_args(
        community=community,
        viewname=url_pattern.name,
        kwargs=required_kwargs,
    )

    assert result == {
        "viewname": f"{expected_prefix}{url_pattern.name}",
        "kwargs": expected_kwargs,
    }
    assert reverse(**result) is not None
