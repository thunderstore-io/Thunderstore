import bleach
import markdown
from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe

from thunderstore.markdown.allowed_tags import (
    ALLOWED_ATTRIBUTES,
    ALLOWED_PROTOCOLS,
    ALLOWED_TAGS,
)

register = template.Library()


def render_markdown(value: str):
    return mark_safe(
        bleach.clean(
            text=markdown.markdown(
                value,
                extensions=[
                    "markdown.extensions.abbr",
                    "markdown.extensions.def_list",
                    "markdown.extensions.fenced_code",
                    "markdown.extensions.footnotes",
                    "markdown.extensions.tables",
                    "markdown.extensions.admonition",
                    # "markdown.extensions.codehilite",  # TODO: Configure
                    "markdown.extensions.nl2br",
                    "markdown.extensions.sane_lists",
                    "markdown.extensions.toc",
                    "markdown.extensions.wikilinks",
                    "pymdownx.magiclink",
                    "pymdownx.tilde",
                ],
            ),
            tags=ALLOWED_TAGS,
            protocols=ALLOWED_PROTOCOLS,
            attributes=ALLOWED_ATTRIBUTES,
        ),
    )


@register.filter
@stringfilter
def markdownify(value):
    return render_markdown(value)
