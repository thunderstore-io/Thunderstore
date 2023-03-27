import pytest
from django.conf import settings
from django.test import Client

from thunderstore.wiki.factories import WikiPageFactory
from thunderstore.wiki.models import Wiki, WikiPage


@pytest.mark.django_db
def test_admin_wiki_list(admin_client: Client) -> None:
    resp = admin_client.get(
        path="/djangoadmin/thunderstore_wiki/wiki/",
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_wiki_detail(admin_client: Client, wiki: Wiki) -> None:
    # Create a page to test the inline
    WikiPageFactory(wiki=wiki)
    path = f"/djangoadmin/thunderstore_wiki/wiki/{wiki.pk}/change/"
    resp = admin_client.get(
        path=path,
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_wiki_page_list(admin_client: Client) -> None:
    resp = admin_client.get(
        path="/djangoadmin/thunderstore_wiki/wikipage/",
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_admin_wiki_page_detail(admin_client: Client, wiki_page: WikiPage) -> None:
    path = f"/djangoadmin/thunderstore_wiki/wikipage/{wiki_page.pk}/change/"
    resp = admin_client.get(
        path=path,
        HTTP_HOST=settings.PRIMARY_HOST,
    )
    assert resp.status_code == 200
