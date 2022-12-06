import base64
import json

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def encode_props(props):
    # Dump to JSON and encode as Base64 to avoid escaping issues.
    # The React components handle decoding in reverse
    encoded = base64.b64encode(json.dumps(props).encode()).decode()
    return mark_safe(f'"{encoded}"')
