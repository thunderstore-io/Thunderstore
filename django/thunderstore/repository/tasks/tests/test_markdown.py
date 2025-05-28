from unittest.mock import patch

import pytest

from thunderstore.cache.utils import get_cache
from thunderstore.repository.tasks.markdown import render_markdown_to_html

RENDER_MARKDOWN_PATH = "thunderstore.markdown.templatetags.markdownify.render_markdown"


def test_markdown_cache_hit_returns_html():
    cache = get_cache("markdown_render")
    cache_key = "rendered_html:test_key:1"
    cache.set(cache_key, "<p>Cached HTML</p>")

    result = render_markdown_to_html("", cache_key, "status_key")
    assert result == "<p>Cached HTML</p>"


def test_markdown_cache_miss_triggers_rendering_task():
    cache = get_cache("markdown_render")
    cache_key = "rendered_html:test_key:1"
    status_key = "rendering_status:test_key:1"

    result = render_markdown_to_html("test markdown", cache_key, status_key)
    assert result == "<p>test markdown</p>\n"
    assert cache.get(cache_key) == "<p>test markdown</p>\n"
    assert cache.get(status_key) is None


def test_markdown_rendering_exception():
    cache = get_cache("markdown_render")
    cache_key = "rendered_html:test_key:1"
    status_key = "rendering_status:test_key:1"

    with pytest.raises(Exception):
        render_markdown_to_html(None, cache_key, status_key)

    assert cache.get(cache_key) is None
    assert cache.get(status_key) is None
