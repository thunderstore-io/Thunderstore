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
