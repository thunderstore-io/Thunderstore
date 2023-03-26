import factory
from factory.django import DjangoModelFactory

from thunderstore.core.factories import UserFactory

from ..wiki.factories import WikiFactory
from .models import (
    Namespace,
    Package,
    PackageRating,
    PackageVersion,
    PackageVersionDownloadEvent,
    PackageWiki,
    Team,
    TeamMember,
)


class NamespaceFactory(DjangoModelFactory):
    class Meta:
        model = Namespace

    name = factory.Sequence(lambda n: f"TestNamespace{n}")


class TeamFactory(DjangoModelFactory):
    class Meta:
        model = Team

    name = factory.Sequence(lambda n: f"TestTeam{n}")


class TeamMemberFactory(DjangoModelFactory):
    class Meta:
        model = TeamMember

    user = factory.SubFactory(UserFactory)
    team = factory.SubFactory(TeamFactory)


class PackageFactory(DjangoModelFactory):
    class Meta:
        model = Package

    owner = factory.SubFactory(TeamFactory)
    name = factory.Faker("first_name")
    namespace = factory.lazy_attribute(
        lambda pkg: NamespaceFactory.create(name=pkg.owner.name, team=pkg.owner)
    )


class PackageRatingFactory(DjangoModelFactory):
    class Meta:
        model = PackageRating

    rater = factory.lazy_attribute(lambda o: UserFactory())
    package = factory.lazy_attribute(lambda o: PackageFactory())


class PackageVersionFactory(DjangoModelFactory):
    class Meta:
        model = PackageVersion

    package = factory.lazy_attribute(lambda o: PackageFactory.create(name=o.name))
    icon = factory.django.ImageField(width=256, height=256)
    name = factory.Sequence(lambda n: f"Package_{n:04d}")
    description = factory.Sequence(lambda n: f"Desc_{n:04d}")
    version_number = "1.0.0"
    file_size = 5242880


class PackageVersionDownloadEventFactory(DjangoModelFactory):
    class Meta:
        model = PackageVersionDownloadEvent

    version = factory.SubFactory(PackageVersionFactory)


class PackageWikiFactory(DjangoModelFactory):
    class Meta:
        model = PackageWiki

    package = factory.SubFactory(PackageFactory)
    wiki = factory.SubFactory(WikiFactory)
