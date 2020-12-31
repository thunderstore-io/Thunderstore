import arrow
from django import template
from django.utils import timezone

register = template.Library()


@register.simple_tag
def humanize_timestamp(timestamp):
    timestamp = arrow.get(timestamp)
    now = arrow.get(timezone.now())
    return timestamp.humanize(now)
