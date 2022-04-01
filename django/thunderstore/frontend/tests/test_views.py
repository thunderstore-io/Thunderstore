import pytest
from django.urls import reverse


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
def test_views_auth_login_link_generation(
    client,
    community_site,
    settings,
    auth_init_host: str,
    auth_exclusive_host: str,
    secure: bool,
) -> None:
    settings.SOCIAL_AUTH_INIT_HOST = auth_init_host
    settings.AUTH_EXCLUSIVE_HOST = auth_exclusive_host
    prefix = f"http{'s' if secure else ''}://{(auth_init_host or auth_exclusive_host) or community_site.site.domain}"
    response = client.get(
        reverse(
            "packages.list",
            kwargs={"community_identifier": community_site.community.identifier},
        ),
        HTTP_HOST=community_site.site.domain,
        secure=secure,
    )
    assert (
        f"{prefix}/auth/login/github/?next=http{'s' if secure else ''}%3A%2F%2Ftestsite.test%2Fc%2Ftest%2F".encode()
        in response.content
    )
    assert (
        f"{prefix}/auth/login/discord/?next=http{'s' if secure else ''}%3A%2F%2Ftestsite.test%2Fc%2Ftest%2F".encode()
        in response.content
    )


@pytest.mark.django_db
@pytest.mark.parametrize("backend", ("discord", "github"))
def test_views_disabled_for_auth_exclusive_host(
    client, community_site, settings, backend: str
):
    response = client.get(
        reverse(
            "packages.list",
            kwargs={"community_identifier": community_site.community.identifier},
        ),
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 200
    settings.AUTH_EXCLUSIVE_HOST = community_site.site.domain
    response = client.get(
        reverse(
            "packages.list",
            kwargs={"community_identifier": community_site.community.identifier},
        ),
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 404
    assert response.content == b"Community not found"
    response = client.get(
        reverse("social:begin", kwargs={"backend": backend}),
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 302
