import markdown
from django import template
from django.template.defaultfilters import stringfilter
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


def deduplicate_escape(text):
    return (
        text.replace("&amp;lt;", "&lt;")
        .replace("&amp;gt;", "&gt;")
        .replace("&amp;quot;", "&quot;")
        .replace("&amp;#39;", "&#39;")
        .replace("&amp;amp;", "&amp;")
    )


@register.filter
@stringfilter
def markdownify(value):
    return mark_safe(
        deduplicate_escape(
            markdown.markdown(
                escape(value),
                extensions=[
                    "markdown.extensions.abbr",
                    "markdown.extensions.def_list",
                    "pymdownx.superfences",
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
            )
        )
    )
