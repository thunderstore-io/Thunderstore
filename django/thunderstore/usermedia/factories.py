import factory
from factory.django import DjangoModelFactory

from thunderstore.core.factories import UserFactory
from thunderstore.usermedia.models import UserMedia


class UserMediaFactory(DjangoModelFactory):
    class Meta:
        model = UserMedia

    owner = factory.SubFactory(UserFactory)
    filename = factory.Sequence(lambda n: f"testfile-{n}")
    key = factory.Sequence(lambda n: f"testfile-{n}")
    size = 2048
