from django import template
from django.urls import reverse

register = template.Library()


@register.simple_tag
def thumbnail_url(image_field, width: int, height: int) -> str:
    if not image_field:
        return ""

    url = (
        reverse("cdn_thumb_redirect", kwargs={"path": image_field.name})
        + f"?width={width}&height={height}"
    )

    return url
