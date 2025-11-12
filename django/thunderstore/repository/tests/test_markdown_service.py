from unittest.mock import patch

import pytest

from thunderstore.cache.utils import get_cache
from thunderstore.repository.services.markdown import render_markdown_service


@pytest.mark.django_db
@pytest.mark.parametrize("markdown, expected_html", [("", ""), ("   ", "")])
def test_render_markdown_empty_input(markdown, expected_html):
    result = render_markdown_service(markdown, "changelog", 1)
    assert result == {"html": expected_html}


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
@pytest.mark.parametrize(
    "side_effect,expected_exception,exception_message",
    [
        (TimeoutError, TimeoutError, "Markdown rendering task timed out."),
        (Exception, Exception, None),
    ],
)
def test_render_markdown_exceptions(
    package_version, side_effect, expected_exception, exception_message
):
    cache = get_cache("markdown_render")
    status_key = f"rendering_status:changelog:{package_version.id}"
    task_id = "mock-task-id"
    cache.set(status_key, task_id)

    get_path = "celery.result.AsyncResult.get"
    id_path = "celery.result.AsyncResult.id"
    with patch(get_path, side_effect=side_effect), patch(id_path, return_value=task_id):
        with pytest.raises(expected_exception, match=exception_message):
            render_markdown_service(
                package_version.changelog, "changelog", package_version.id
            )
        assert cache.get(status_key) is None
