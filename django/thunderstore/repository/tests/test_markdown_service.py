from unittest.mock import patch

import pytest

from thunderstore.cache.utils import get_cache
from thunderstore.repository.services.markdown import render_markdown_service


@pytest.mark.django_db
def test_render_markdown_empty_input():
    result = render_markdown_service("", "changelog", 1)
    assert result == {"html": ""}

    result = render_markdown_service("    ", "changelog", 1)
    assert result == {"html": ""}


@pytest.mark.django_db
def test_render_markdown_cached_html(package_version):
    cache = get_cache("markdown_render")
    cache_key = f"rendered_html:changelog:{package_version.id}"
    cache.set(cache_key, "<p>Cached HTML</p>")

    result = render_markdown_service(
        package_version.changelog, "changelog", package_version.id
    )
    assert result == {"html": "<p>Cached HTML</p>"}


@pytest.mark.django_db
def test_render_markdown_no_cached_html(package_version):
    cache = get_cache("markdown_render")
    cache_key = f"rendered_html:changelog:{package_version.id}"
    cache.delete(cache_key)

    result = render_markdown_service(
        package_version.changelog, "changelog", package_version.id
    )
    assert result == {"html": "<h1>This is an example changelog</h1>\n"}


@pytest.mark.django_db
def test_render_markdown_in_progress(package_version):
    cache = get_cache("markdown_render")
    status_key = f"rendering_status:changelog:{package_version.id}"
    cache.set(status_key, "in_progress")

    with patch("time.sleep") as sleep_mock:
        result = render_markdown_service(
            package_version.changelog, "changelog", package_version.id
        )
        assert result == {"html": "<em>Loading...</em>"}
        sleep_mock.assert_called()


@pytest.mark.django_db
def test_render_markdown_html_available_after_wait(package_version):
    cache = get_cache("markdown_render")
    status_key = f"rendering_status:changelog:{package_version.id}"
    cache_key = f"rendered_html:changelog:{package_version.id}"

    cache.set(status_key, "in_progress")

    def mock_cache_get(key):
        if key == cache_key:
            return "<p>Rendered HTML</p>"
        return None

    with patch("time.sleep"), patch.object(cache, "get", side_effect=mock_cache_get):
        result = render_markdown_service(
            package_version.changelog, "changelog", package_version.id
        )
        assert result == {"html": "<p>Rendered HTML</p>"}


@pytest.mark.django_db
def test_render_markdown_html_unavailable_after_wait(package_version):
    cache = get_cache("markdown_render")
    status_key = f"rendering_status:changelog:{package_version.id}"

    cache.set(status_key, "in_progress")

    with patch("time.sleep"), patch.object(cache, "get", return_value=None):
        result = render_markdown_service(
            package_version.changelog, "changelog", package_version.id
        )
        assert result == {"html": "<em>Loading...</em>"}
