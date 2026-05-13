from typing import Any

import pytest
from django.test import RequestFactory
from django.utils.encoding import iri_to_uri

from thunderstore.community.middleware import CommunitySiteMiddleware
from thunderstore.community.models import Community


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


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path, expect_community",
    (
        ("/", True),
        ("/any/path/", True),
        ("/c/some_community/", True),
        ("/admin/", False),
    ),
)
def test_community_site_middleware_old_exclusive_host(
    settings: Any, path: str, expect_community: bool
) -> None:
    # Ensure the community exists so get_default_community finds it
    Community.objects.get_or_create(identifier="riskofrain2", defaults={"name": "Risk of Rain 2"})

    settings.OLD_EXCLUSIVE_HOST = "old.thunderstore.localhost"
    settings.AUTH_EXCLUSIVE_HOST = "auth.thunderstore.localhost"
    settings.PRIMARY_HOST = "thunderstore.localhost"

    request = RequestFactory().get(path, HTTP_HOST="old.thunderstore.localhost")

    def mock_get_response(req):
        from django.http import HttpResponse

        return HttpResponse(b"OK", status=200)

    middleware = CommunitySiteMiddleware(mock_get_response)
    response = middleware(request)

    assert response.status_code == 200
    assert response.content == b"OK"
    assert request.site is None

    if expect_community:
        assert request.community is not None
        assert request.community.identifier == "riskofrain2"
    else:
        assert request.community is None


@pytest.mark.django_db
def test_community_site_middleware_old_exclusive_host_missing_community(
    settings: Any,
) -> None:
    # Deliberately do not create the riskofrain2 community row
    settings.OLD_EXCLUSIVE_HOST = "old.thunderstore.localhost"
    settings.AUTH_EXCLUSIVE_HOST = "auth.thunderstore.localhost"
    settings.PRIMARY_HOST = None

    request = RequestFactory().get("/", HTTP_HOST="old.thunderstore.localhost")

    middleware = CommunitySiteMiddleware(lambda req: None)
    response = middleware(request)

    assert response.status_code == 404
    assert b"Community not found" in response.content
