from celery import shared_task

from thunderstore.cache.utils import get_cache
from thunderstore.core.settings import CeleryQueues
from thunderstore.markdown.templatetags.markdownify import render_markdown

cache = get_cache("markdown_render")


@shared_task(
    queue=CeleryQueues.BackgroundMarkdownRender,
    name="thunderstore.repository.tasks.render_markdown",
)
def render_markdown_to_html(
    markdown: str,
    cache_key: str,
) -> str:
    cached_html = cache.get(cache_key)
    if cached_html is not None:
        return cached_html

    try:
        html = render_markdown(markdown)
    except Exception as error:
        raise error

    cache.set(cache_key, html)
    return html
