from django import template
from django.utils.safestring import mark_safe

from frontend.models import DynamicHTML


register = template.Library()


@register.simple_tag
def dynamic_html(placement):
    dynamic_content = (
        DynamicHTML.objects
        .filter(is_active=True, placement=placement)
        .values_list("content", flat=True)
    )
    content = "".join(dynamic_content)
    return mark_safe(content)
