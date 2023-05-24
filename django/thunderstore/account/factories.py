import factory
from factory import LazyAttribute, SubFactory
from factory.django import DjangoModelFactory

from thunderstore.account.models import ServiceAccount, UserFlag, UserFlagMembership
from thunderstore.account.tokens import (
    get_service_account_api_token,
    hash_service_account_api_token,
)
from thunderstore.core.factories import UserFactory
from thunderstore.repository.factories import TeamFactory


class ServiceAccountFactory(DjangoModelFactory):
    class Meta:
        model = ServiceAccount

    class Params:
        plaintext_token = None

    user = SubFactory(UserFactory)
    owner = SubFactory(TeamFactory)
    api_token = LazyAttribute(
        lambda o: hash_service_account_api_token(
            o.plaintext_token or get_service_account_api_token()
        )
    )


class UserFlagFactory(DjangoModelFactory):
    class Meta:
        model = UserFlag

    name = factory.Sequence(lambda n: f"Test Flag {n}")
    identifier = factory.Sequence(lambda n: f"test-flag-{n}")


class UserFlagMembershipFactory(DjangoModelFactory):
    class Meta:
        model = UserFlagMembership

    user = SubFactory(UserFactory)
    flag = SubFactory(UserFlagFactory)
