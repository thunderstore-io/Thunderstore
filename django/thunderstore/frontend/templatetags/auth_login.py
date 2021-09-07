from urllib.parse import ParseResult, parse_qs, urlencode, urlparse, urlunparse

from django import template
from django.urls import reverse
from django.utils.http import urlencode

register = template.Library()


@register.simple_tag(takes_context=True)
def add_auth_login_link(context, backend):
    parts = urlparse(reverse("social:begin", kwargs={"backend": backend}))
    query_dict = parse_qs(parts.query)
    query_dict["next"] = [context.request.build_absolute_uri()]
    modified = ParseResult(
        scheme=parts.scheme,
        netloc=parts.netloc,
        path=parts.path,
        params=parts.params,
        query=urlencode(query_dict, doseq=True),
        fragment=parts.fragment,
    )
    result = urlunparse(modified)
    return result
