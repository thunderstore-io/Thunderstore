from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from thunderstore.community.models import CommunitySite


@pytest.mark.django_db
def test_api_docs(client: APIClient, community_site: CommunitySite):
    response = client.get(
        "/api/docs/?format=openapi",
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_views_markdown_preview(client, community_site):
    response = client.get(
        reverse("tools.markdown-preview"),
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_views_manifest_v1_validator(client, community_site):
    response = client.get(
        reverse("tools.manifest-v1-validator"),
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize("auth_init_host", (None, "init.localhost"))
@pytest.mark.parametrize("auth_exclusive_host", (None, "auth.localhost"))
@pytest.mark.parametrize("secure", (False, True))
@pytest.mark.parametrize("old_urls", (False, True))
def test_views_auth_login_link_generation(
    client,
    community_site,
    settings,
    auth_init_host: str,
    auth_exclusive_host: str,
    secure: bool,
    old_urls: bool,
) -> None:
    settings.SOCIAL_AUTH_INIT_HOST = auth_init_host
    settings.AUTH_EXCLUSIVE_HOST = auth_exclusive_host
    prefix = f"http{'s' if secure else ''}://{(auth_init_host or auth_exclusive_host) or community_site.site.domain}"
    if old_urls:
        response = client.get(
            reverse("old_urls:packages.list"),
            HTTP_HOST=community_site.site.domain,
            secure=secure,
        )
        assert (
            f"{prefix}/auth/login/github/?next=http{'s' if secure else ''}%3A%2F%2Ftestsite.test%2Fpackage%2F".encode()
            in response.content
        )
        assert (
            f"{prefix}/auth/login/discord/?next=http{'s' if secure else ''}%3A%2F%2Ftestsite.test%2Fpackage%2F".encode()
            in response.content
        )
    else:
        response = client.get(
            reverse(
                "communities:community:packages.list",
                kwargs={"community_identifier": community_site.community.identifier},
            ),
            HTTP_HOST=community_site.site.domain,
            secure=secure,
        )
        assert (
            f"{prefix}/auth/login/github/?next=http{'s' if secure else ''}%3A%2F%2Ftestsite.test%2Fc%2F{community_site.community.identifier}%2F".encode()
            in response.content
        )
        assert (
            f"{prefix}/auth/login/discord/?next=http{'s' if secure else ''}%3A%2F%2Ftestsite.test%2Fc%2F{community_site.community.identifier}%2F".encode()
            in response.content
        )


@pytest.mark.django_db
@pytest.mark.parametrize("backend", ("discord", "github"))
@pytest.mark.parametrize("as_primary", (False, True))
@pytest.mark.parametrize("old_urls", (False, True))
def test_views_disabled_for_auth_exclusive_host(
    client,
    community_site,
    settings,
    backend: str,
    as_primary: bool,
    old_urls: bool,
):
    if old_urls:
        url = reverse("old_urls:packages.list")
    else:
        url = reverse(
            "communities:community:packages.list",
            kwargs={"community_identifier": community_site.community.identifier},
        )
    response = client.get(
        url,
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 200
    settings.AUTH_EXCLUSIVE_HOST = community_site.site.domain

    if as_primary:
        settings.PRIMARY_HOST = community_site.site.domain
    else:
        settings.PRIMARY_HOST = community_site.site.domain + "test"

    response = client.get(
        url,
        HTTP_HOST=community_site.site.domain,
    )

    if as_primary:
        assert response.status_code == 404
        assert response.content == b"Community not found"
    else:
        assert response.status_code == 302
        assert response["Location"] == f"{settings.PROTOCOL}{settings.PRIMARY_HOST}/"

    response = client.get(
        reverse("social:begin", kwargs={"backend": backend}),
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 302


@pytest.mark.django_db
def test_thumbnail_redirect_success(dummy_cover_image, client, community_site):
    community = community_site.community
    community.cover_image = dummy_cover_image
    community.save()

    url = reverse("cdn_thumb_redirect", kwargs={"path": community.cover_image.name})
    params = {"width": 100, "height": 100}

    response = client.get(url, params, HTTP_HOST=community_site.site.domain)

    assert response.status_code == 302
    assert response["Location"].endswith(".jpg")
    assert "Cache-Control" in response
    assert "max-age=86400" in response["Cache-Control"]


@pytest.mark.django_db
def test_thumbnail_redirect_exception(dummy_cover_image, community_site, client):
    community = community_site.community
    community.cover_image = dummy_cover_image
    community.save()

    url = reverse("cdn_thumb_redirect", kwargs={"path": community.cover_image.name})
    params = {"width": 100, "height": 100}

    path = "thunderstore.frontend.views.get_or_create_thumbnail"
    with patch(path) as mock_get_thumbnail:
        mock_get_thumbnail.return_value = None
        response = client.get(url, params, HTTP_HOST=community_site.site.domain)

    assert response.status_code == 404
    assert "Cache-Control" in response
    assert "max-age=86400" in response["Cache-Control"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "params",
    [
        {"width": "abc", "height": "100"},
        {"width": "100", "height": "abc"},
        {"width": "0", "height": "100"},
        {"width": "100", "height": "0"},
        {"width": "-1", "height": "100"},
        {},
    ],
)
def test_thumbnail_redirect_invalid_params_returns_fallback(
    params, dummy_cover_image, client, community_site
):
    community = community_site.community
    community.cover_image = dummy_cover_image
    community.save()

    url = reverse("cdn_thumb_redirect", kwargs={"path": community.cover_image.name})
    response = client.get(url, params, HTTP_HOST=community_site.site.domain)

    assert response.status_code == 404
    assert "Cache-Control" in response
    assert "max-age=86400" in response["Cache-Control"]


@pytest.mark.django_db
def test_thumbnail_serve_success(dummy_cover_image, client, community_site):
    community = community_site.community
    community.cover_image = dummy_cover_image
    community.save()

    url = reverse("cdn_thumb_serve", kwargs={"path": community.cover_image.name})
    params = {"width": 100, "height": 100}

    response = client.get(url, params, HTTP_HOST=community_site.site.domain)
    assert response.status_code == 200
    assert response.get("Content-Type") == "image/jpeg"
    assert response.get("Cache-Control") == "max-age=86400, public"
    assert response.get("Content-Disposition").startswith("inline; filename=")
