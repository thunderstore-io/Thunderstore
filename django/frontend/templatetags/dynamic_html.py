from django import template
from django.utils.safestring import mark_safe

from frontend.models import DynamicHTML


register = template.Library()


@register.simple_tag
def dynamic_head():
    dynamic_head = (
        DynamicHTML.objects.filter(is_active=True)
        .values_list("head_content", flat=True)
    )
    content = "".join(dynamic_head)
    return mark_safe(content)


@register.simple_tag
def dynamic_body():
    dynamic_head = (
        DynamicHTML.objects.filter(is_active=True)
        .values_list("body_content", flat=True)
    )
    content = "".join(dynamic_head)
    return mark_safe(content)
