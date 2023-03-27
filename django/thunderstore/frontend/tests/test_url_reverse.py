import pytest
from django.urls import URLPattern, reverse

from thunderstore.community.factories import CommunitySiteFactory
from thunderstore.community.models import Community
from thunderstore.frontend.tests.utils import get_url_kwarg
from thunderstore.frontend.url_reverse import get_community_url_reverse_args
from thunderstore.repository.urls import package_urls


@pytest.mark.django_db
@pytest.mark.parametrize("url_pattern", [x for x in package_urls if hasattr(x, "name")])
@pytest.mark.parametrize("with_site", (False, True))
def test_get_community_url_reverse_args(
    community: Community,
    url_pattern: URLPattern,
    with_site: bool,
) -> None:

    required_kwargs = {
        k: get_url_kwarg(k) for k in url_pattern.pattern.regex.groupindex.keys()
    }
    required_kwargs = required_kwargs if required_kwargs else None

    if with_site:
        CommunitySiteFactory(community=community)
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
