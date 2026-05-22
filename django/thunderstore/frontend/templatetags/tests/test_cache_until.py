from typing import Optional
from unittest.mock import MagicMock, patch

from django.template import Context, Template

from thunderstore.cache.enums import CacheBustCondition


def render_cache_until(expiry: Optional[int]) -> None:
    condition = CacheBustCondition.background_update_only
    template = Template(
        "{% load cache_until %}"
        f"{{% cache_until condition 'frag' {expiry} %}}"
        "content"
        "{% endcache %}"
    )
    template.render(Context({"condition": condition}))


@patch("thunderstore.frontend.templatetags.cache_until.cache_get_or_set")
def test_debug_cache_ttl_overrides_expiry(mock_cache: MagicMock, settings) -> None:
    settings.DEBUG = True
    settings.DEBUG_CACHE_TTL = 10
    render_cache_until(300)
    _, kwargs = mock_cache.call_args
    assert kwargs["expiry"] == 10


@patch("thunderstore.frontend.templatetags.cache_until.cache_get_or_set")
def test_debug_cache_ttl_overrides_null_expiry(mock_cache: MagicMock, settings) -> None:
    settings.DEBUG = True
    settings.DEBUG_CACHE_TTL = 10
    render_cache_until(None)
    _, kwargs = mock_cache.call_args
    assert kwargs["expiry"] == 10


@patch("thunderstore.frontend.templatetags.cache_until.cache_get_or_set")
def test_debug_cache_ttl_none_leaves_expiry(mock_cache: MagicMock, settings) -> None:
    settings.DEBUG = True
    settings.DEBUG_CACHE_TTL = None
    render_cache_until(300)
    _, kwargs = mock_cache.call_args
    assert kwargs["expiry"] == 300


@patch("thunderstore.frontend.templatetags.cache_until.cache_get_or_set")
def test_debug_cache_ttl_no_effect_outside_debug(
    mock_cache: MagicMock, settings
) -> None:
    settings.DEBUG = False
    settings.DEBUG_CACHE_TTL = 10
    render_cache_until(300)
    _, kwargs = mock_cache.call_args
    assert kwargs["expiry"] == 300
