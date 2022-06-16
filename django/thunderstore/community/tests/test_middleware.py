from typing import Any

import pytest
from django.test import RequestFactory
from django.utils.encoding import iri_to_uri

from thunderstore.community.middleware import CommunitySiteMiddleware


@pytest.mark.parametrize("protocol", ("http://", "https://"))
@pytest.mark.parametrize(
    "primary_domain, status, content",
    (
        (None, 404, b"Community not found"),
        ("localhost", 302, None),
        ("thunderstore.localhost", 302, None),
    ),
)
def test_community_site_middleware_get_404(
    protocol: str,
    primary_domain: str,
    status: int,
    content: bytes,
    settings: Any,
) -> None:
    settings.PRIMARY_HOST = primary_domain
    settings.PROTOCOL = protocol
    request = RequestFactory().get("", secure=protocol == "https://")
    response = CommunitySiteMiddleware(None).get_404(request)
    assert response.status_code == status
    if content:
        assert content in response.content
    if status == 302:
        assert response["Location"] == iri_to_uri(f"{protocol}{primary_domain}/")
