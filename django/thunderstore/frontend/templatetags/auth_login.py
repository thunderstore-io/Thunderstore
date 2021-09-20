from urllib.parse import ParseResult, parse_qs, urlencode, urlparse, urlunparse

from django import template
from django.conf import settings
from django.urls import reverse
from django.utils.http import urlencode

register = template.Library()


def get_auth_init_host(request_host: str) -> str:
    return (
        settings.SOCIAL_AUTH_INIT_HOST or settings.AUTH_EXCLUSIVE_HOST or request_host
    )


@register.simple_tag(takes_context=True)
def add_auth_login_link(context, backend) -> str:
    parts = urlparse(
        context.request.build_absolute_uri(
            reverse("social:begin", kwargs={"backend": backend})
        )
    )
    query_dict = parse_qs(parts.query)
    query_dict[b"next"] = [context.request.build_absolute_uri()]
    netloc = get_auth_init_host(parts.netloc)
    scheme = (parts.scheme or "https") if netloc else ""
    modified = ParseResult(
        scheme=scheme,
        netloc=netloc,
        path=parts.path,
        params=parts.params,
        query=urlencode(query_dict, doseq=True),
        fragment=parts.fragment,
    )
    return str(urlunparse(modified))
