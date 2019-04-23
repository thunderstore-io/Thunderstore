import markdown

from django import template
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.template.defaultfilters import stringfilter

register = template.Library()


def deduplicate_escape(text):
    return (text
            .replace("&amp;lt;", "&lt;")
            .replace("&amp;gt;", "&gt;")
            .replace("&amp;quot;", "&quot;")
            .replace("&amp;#39;", "&#39;")
            )


@register.filter
@stringfilter
def markdownify(value):
    return mark_safe(deduplicate_escape(markdown.markdown(
        escape(value),
        extensions=[
            "markdown.extensions.fenced_code",
            "markdown.extensions.tables",
        ]
    )))
