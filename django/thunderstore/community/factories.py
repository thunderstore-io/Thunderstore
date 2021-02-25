import factory
from factory.django import DjangoModelFactory

from .models import Community


class CommunityFactory(DjangoModelFactory):
    class Meta:
        model = Community

    name = factory.Sequence(lambda n: f"TestCommunity{n}")
    identifier = factory.Sequence(lambda n: f"test-community-{n}")
