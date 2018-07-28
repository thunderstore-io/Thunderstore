import markdown

from django import template
from django.utils.safestring import mark_safe
from django.utils.html import strip_tags
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter
@stringfilter
def markdownify(value):
    return mark_safe(markdown.markdown(
        strip_tags(value),
        extensions=["markdown.extensions.fenced_code"]
    ))
