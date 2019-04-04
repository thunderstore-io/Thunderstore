import markdown

from django import template
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter
@stringfilter
def markdownify(value):
    return mark_safe(markdown.markdown(
        escape(value),
        extensions=[
            "markdown.extensions.fenced_code",
            "markdown.extensions.tables",
        ]
    ))
