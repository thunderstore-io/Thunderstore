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
def test_views_auth_login_link_generation(client, community_site):
    response = client.get(
        reverse("packages.list"),
        HTTP_HOST=community_site.site.domain,
    )
    assert (
        b"/auth/login/github/?next=http%3A%2F%2Ftestsite.test%2Fpackage%2F"
        in response._container[0]
    )
    assert (
        b"/auth/login/discord/?next=http%3A%2F%2Ftestsite.test%2Fpackage%2F"
        in response._container[0]
    )
