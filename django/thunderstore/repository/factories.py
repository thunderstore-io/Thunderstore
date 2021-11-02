import factory
from factory.django import DjangoModelFactory

from thunderstore.core.factories import UserFactory

from .models import (
    Namespace,
    Package,
    PackageVersion,
    PackageVersionDownloadEvent,
    Team,
    TeamMember,
)


class TeamFactory(DjangoModelFactory):
    class Meta:
        model = Team

    name = factory.Sequence(lambda n: f"TestTeam{n}")


class TeamMemberFactory(DjangoModelFactory):
    class Meta:
        model = TeamMember

    user = factory.SubFactory(UserFactory)
    team = factory.SubFactory(TeamFactory)


class NamespaceFactory(DjangoModelFactory):
    class Meta:
        model = Namespace

    name = factory.Sequence(lambda n: f"TestNamespace{n}")


class PackageFactory(DjangoModelFactory):
    class Meta:
        model = Package

    owner = factory.SubFactory(NamespaceFactory)
    name = factory.Faker("first_name")


class PackageVersionFactory(DjangoModelFactory):
    class Meta:
        model = PackageVersion

    package = factory.lazy_attribute(lambda o: PackageFactory.create(name=o.name))
    icon = factory.django.ImageField(width=256, height=256)
    name = factory.Sequence(lambda n: f"Package_{n:04d}")
    version_number = "1.0.0"
    file_size = 5242880


class PackageVersionDownloadEventFactory(DjangoModelFactory):
    class Meta:
        model = PackageVersionDownloadEvent

    version = factory.SubFactory(PackageVersionFactory)
