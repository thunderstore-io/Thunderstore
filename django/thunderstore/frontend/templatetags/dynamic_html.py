from typing import List

from django import template
from django.utils.safestring import mark_safe

from thunderstore.account.utils import get_request_user_flags
from thunderstore.cache.cache import cache_function_result
from thunderstore.cache.enums import CacheBustCondition
from thunderstore.community.models import Community
from thunderstore.frontend.models import DynamicHTML

register = template.Library()


@cache_function_result(cache_until=CacheBustCondition.dynamic_html_updated)
def get_dynamic_html_content(
    community: Community, placement: str, user_flags: List[str]
) -> str:
    entries = DynamicHTML.get_for_community(
        community=community,
        placement=placement,
        user_flags=user_flags,
    ).values_list("content", flat=True)
    return "".join(entries)


@register.simple_tag(takes_context=True)
def dynamic_html(context, placement):
    community = context.get("community", None)
    request = context["request"]
    if not community and hasattr(request, "community"):
        community = request.community
    flags = get_request_user_flags(request)
    return mark_safe(get_dynamic_html_content(community, placement, flags))
