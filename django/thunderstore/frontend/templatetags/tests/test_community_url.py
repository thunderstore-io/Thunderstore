import pytest
from django.template import Context, Template, TemplateSyntaxError
from django.urls import URLPattern, reverse

from thunderstore.community.factories import CommunitySiteFactory
from thunderstore.community.models import Community
from thunderstore.frontend.url_reverse import get_community_url_reverse_args
from thunderstore.repository.urls import package_urls


@pytest.mark.django_db
@pytest.mark.parametrize("url_pattern", [x for x in package_urls if hasattr(x, "name")])
@pytest.mark.parametrize("with_site", (False, True))
def test_tag_community_url_valid(
    community: Community,
    url_pattern: URLPattern,
    with_site: bool,
) -> None:
    if with_site:
        CommunitySiteFactory(community=community)

    kwargs = {k: "test" for k in url_pattern.pattern.regex.groupindex.keys()}
    args = " ".join([f"{k}='{v}'" for k, v in kwargs.items()])
    template = (
        f"{{% load community_url %}}{{% community_url '{url_pattern.name}' {args} %}}"
    )

    rendered = Template(template).render(Context({"community": community}))
    expected = reverse(
        **get_community_url_reverse_args(
            community=community,
            viewname=url_pattern.name,
            kwargs=kwargs,
        )
    )

    assert expected in rendered


def test_tag_community_url_no_args():
    template = "{% load community_url %}{% community_url 'packages.list' 'test' %}"
    with pytest.raises(
        TemplateSyntaxError, match="Only kwargs are supported by 'community_url'"
    ):
        Template(template).render(Context({}))


def test_tag_community_url_no_asvar():
    template = "{% load community_url %}{% community_url 'packages.list' as url %}"
    with pytest.raises(
        TemplateSyntaxError, match="'as' is not supported by 'community_url'"
    ):
        Template(template).render(Context({}))
