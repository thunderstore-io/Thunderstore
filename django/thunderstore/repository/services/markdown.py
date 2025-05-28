import time

from thunderstore.cache.utils import get_cache
from thunderstore.repository.tasks.markdown import render_markdown_to_html

cache = get_cache("markdown_render")


def render_markdown_service(markdown: str, key: str, object_id: int) -> dict:
    if markdown.strip() == "":
        return {"html": ""}

    cache_key = f"rendered_html:{key}:{object_id}"
    status_key = f"rendering_status:{key}:{object_id}"

    html = cache.get(cache_key)
    if html is not None:
        return {"html": html}

    if cache.get(status_key) is None:
        cache.set(status_key, "in_progress", timeout=300)
        render_markdown_to_html.delay(
            markdown=markdown,
            cache_key=cache_key,
            status_key=status_key,
        )

    for _ in range(5):  # wait up to 5s total
        html = cache.get(cache_key)
        if html is not None:
            return {"html": html}
        time.sleep(1)

    return {"html": "<em>Loading...</em>"}
