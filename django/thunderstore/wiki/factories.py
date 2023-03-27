import factory
from factory.django import DjangoModelFactory

from thunderstore.wiki.models import Wiki, WikiPage


class WikiFactory(DjangoModelFactory):
    class Meta:
        model = Wiki

    title = factory.Sequence(lambda n: f"Test Wiki {n}")


class WikiPageFactory(DjangoModelFactory):
    class Meta:
        model = WikiPage

    wiki = factory.SubFactory(WikiFactory)
    title = factory.Sequence(lambda n: f"Test Page {n}")
    markdown_content = factory.Faker("sentence")
