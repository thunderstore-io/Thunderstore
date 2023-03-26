import pytest
from rest_framework.test import APIClient

from thunderstore.wiki.models import WikiPage


@pytest.mark.django_db
def test_api_experimental_wiki_page(
    api_client: APIClient,
    wiki_page: WikiPage,
):
    response = api_client.get(
        f"/api/experimental/wiki/page/{wiki_page.pk}/",
        HTTP_ACCEPT="application/json",
    )
    assert response.status_code == 200
    result = response.json()
    assert result["markdown_content"] == wiki_page.markdown_content
    assert result["title"] == wiki_page.title
    assert result["slug"] == f"{wiki_page.pk}-{wiki_page.slug}"
