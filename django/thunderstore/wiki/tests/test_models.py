import pytest

from thunderstore.wiki.factories import WikiPageFactory
from thunderstore.wiki.models import Wiki, WikiPage


@pytest.mark.django_db
def test_wiki_datetime_updated_on_page_save(
    wiki: Wiki,
    wiki_page: WikiPage,
) -> None:
    ts1 = wiki.datetime_updated
    wiki_page.save()
    wiki.refresh_from_db()
    ts2 = wiki.datetime_updated
    assert ts1 < ts2
    WikiPageFactory(wiki=wiki)
    wiki.refresh_from_db()
    ts3 = wiki.datetime_updated
    assert ts2 < ts3
    wiki_page.delete()
    wiki.refresh_from_db()
    ts4 = wiki.datetime_updated
    assert ts3 < ts4
