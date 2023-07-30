import factory
from factory.django import DjangoModelFactory

from thunderstore.schema_server.models import SchemaChannel


class SchemaChannelFactory(DjangoModelFactory):
    class Meta:
        model = SchemaChannel

    identifier = factory.Sequence(lambda n: f"test-channel-{n}")
