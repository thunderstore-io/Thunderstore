import factory
from django.contrib.sites.models import Site
from factory.django import DjangoModelFactory

from .models import Community, CommunitySite


class SiteFactory(DjangoModelFactory):
    class Meta:
        model = Site

    domain = factory.Sequence(lambda n: f"test-domain-{n}.example.org")
    name = factory.Sequence(lambda n: f"Test Domain {n}")


class CommunityFactory(DjangoModelFactory):
    class Meta:
        model = Community

    name = factory.Sequence(lambda n: f"TestCommunity{n}")
    identifier = factory.Sequence(lambda n: f"test-community-{n}")


class CommunitySiteFactory(DjangoModelFactory):
    class Meta:
        model = CommunitySite

    community = factory.SubFactory(CommunityFactory)
    site = factory.SubFactory(SiteFactory)
