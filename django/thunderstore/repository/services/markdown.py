from celery.result import AsyncResult

from thunderstore.cache.utils import get_cache
from thunderstore.repository.tasks.markdown import render_markdown_to_html

cache = get_cache("markdown_render")


def render_markdown_service(markdown: str, key: str, object_id: int) -> dict:
    if markdown.strip() == "":
        return {"html": ""}

    cache_key = f"rendered_html:{key}:{object_id}"
    status_key = f"rendering_status:{key}:{object_id}"

    if (html := cache.get(cache_key)) is not None:
        return {"html": html}

    if task_id := cache.get(status_key):
        task = AsyncResult(id=task_id)
    else:
        task = render_markdown_to_html.delay(markdown=markdown, cache_key=cache_key)
        cache.set(status_key, task.id, timeout=300)

    try:
        result = task.get(timeout=5)
        cache.delete(status_key)
        return {"html": result}
    except TimeoutError:
        cache.delete(status_key)
        raise TimeoutError("Markdown rendering task timed out.")
    except Exception as error:
        cache.delete(status_key)
        raise error
