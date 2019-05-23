from django import template
from django.utils.safestring import mark_safe

from frontend.models import DynamicHTML

from core.cache import (
    CacheBustCondition,
    cache_function_result
)

register = template.Library()


@cache_function_result(cache_until=CacheBustCondition.dynamic_html_updated)
def get_dynamic_html_content(placement):
    dynamic_content = (
        DynamicHTML.objects
        .filter(is_active=True, placement=placement)
        .order_by("-ordering", "-pk")
        .values_list("content", flat=True)
    )
    return "".join(dynamic_content)


@register.simple_tag
def dynamic_html(placement):
    return mark_safe(get_dynamic_html_content(placement))
