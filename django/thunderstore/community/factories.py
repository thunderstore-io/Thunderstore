import factory
from django.contrib.sites.models import Site
from factory.django import DjangoModelFactory

from thunderstore.repository.factories import PackageVersionFactory

from .models import Community, CommunitySite, PackageCategory, PackageListing


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

    @classmethod
    def create_batch(cls, size=1, **kwargs):
        return [
            cls(**{**kwargs, "identifier": f"test-community-{i}"}) for i in range(size)
        ]


class PackageCategoryFactory(DjangoModelFactory):
    class Meta:
        model = PackageCategory

    community = factory.SubFactory(CommunityFactory)
    name = factory.Sequence(lambda n: f"TestCategory{n}")
    slug = factory.Sequence(lambda n: f"test-category-{n}")


class CommunitySiteFactory(DjangoModelFactory):
    class Meta:
        model = CommunitySite

    community = factory.SubFactory(CommunityFactory)
    site = factory.SubFactory(SiteFactory)


class PackageListingFactory(DjangoModelFactory):
    class Meta:
        model = PackageListing

    class Params:
        community_ = None
        community_kwargs = {}
        package_ = None
        package_kwargs = {}
        package_version_kwargs = {}

    @factory.lazy_attribute
    def community(self):
        """
        To use an existing community, pass it via community_ parameter.

        To create a new package with custom values, pass the values via
        community_kwargs parameter.
        """
        if self.community_:
            return self.community_

        site = CommunitySiteFactory()

        if self.community_kwargs:
            for attr, value in self.community_kwargs.items():
                setattr(site.community, attr, value)

            site.community.save()

        return site.community

    @factory.lazy_attribute
    def package(self):
        """
        To use an existing package, pass it via package_ parameter.

        To create a new package with custom values, pass the values via
        package_kwargs parameter.
        """
        if self.package_:
            return self.package_

        ver = PackageVersionFactory(**self.package_version_kwargs)

        if self.package_kwargs:
            for attr, value in self.package_kwargs.items():
                setattr(ver.package, attr, value)

            ver.package.save()

        return ver.package

    @factory.post_generation
    def categories(self, create, extracted, **kwargs):
        """
        Allow passing categories for M2M relation.
        """
        if create and extracted:
            self.categories.set(extracted)
