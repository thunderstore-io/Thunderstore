import factory

from core.factories import UserFactory

from .models import UploaderIdentity
from .models import UploaderIdentityMember
from .models import Package
from .models import PackageVersion
from .models import PackageVersionDownloadEvent


class UploaderIdentityFactory(factory.DjangoModelFactory):
    class Meta:
        model = UploaderIdentity

    name = factory.Faker("first_name")


class UploaderIdentityMemberFactory(factory.DjangoModelFactory):
    class Meta:
        model = UploaderIdentityMember

    user = factory.SubFactory(UserFactory)
    identity = factory.SubFactory(UploaderIdentityFactory)


class PackageFactory(factory.DjangoModelFactory):
    class Meta:
        model = Package

    owner = factory.SubFactory(UploaderIdentityFactory)
    name = factory.Faker("first_name")


class PackageVersionFactory(factory.DjangoModelFactory):
    class Meta:
        model = PackageVersion

    package = factory.SubFactory(PackageFactory)
    icon = factory.django.ImageField(width=256, height=256)
    name = factory.Faker("first_name")
    version_number = "1.0.0"


class PackageVersionDownloadEventFactory(factory.DjangoModelFactory):
    class Meta:
        model = PackageVersionDownloadEvent

    version = factory.SubFactory(PackageVersionFactory)
