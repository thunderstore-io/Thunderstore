from django import template
from django.utils.safestring import mark_safe

from thunderstore.core.cache import CacheBustCondition, cache_function_result
from thunderstore.frontend.models import DynamicHTML

register = template.Library()


@cache_function_result(cache_until=CacheBustCondition.dynamic_html_updated)
def get_dynamic_html_content(community, placement):
    entries = DynamicHTML.get_for_community(community, placement).values_list(
        "content",
        flat=True,
    )
    return "".join(entries)


@register.simple_tag(takes_context=True)
def dynamic_html(context, placement):
    community = context["request"].community
    return mark_safe(get_dynamic_html_content(community, placement))
