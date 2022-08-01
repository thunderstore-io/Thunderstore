import bleach
from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
from markdown_it import MarkdownIt

from thunderstore.markdown.allowed_tags import (
    ALLOWED_ATTRIBUTES,
    ALLOWED_PROTOCOLS,
    ALLOWED_TAGS,
)

register = template.Library()
md = MarkdownIt("gfm-like")


def render_markdown(value: str):
    if value.startswith("\ufeff"):
        value = value[1:]
    return mark_safe(
        bleach.clean(
            text=md.render(value.strip()),
            tags=ALLOWED_TAGS,
            protocols=ALLOWED_PROTOCOLS,
            attributes=ALLOWED_ATTRIBUTES,
        ),
    )


@register.filter
@stringfilter
def markdownify(value):
    return render_markdown(value)
