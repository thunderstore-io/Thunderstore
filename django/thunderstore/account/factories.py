from factory import LazyAttribute, SubFactory
from factory.django import DjangoModelFactory

from thunderstore.account.models import ServiceAccount
from thunderstore.account.tokens import (
    get_service_account_api_token,
    hash_service_account_api_token,
)
from thunderstore.core.factories import UserFactory
from thunderstore.repository.factories import UploaderIdentityFactory


class ServiceAccountFactory(DjangoModelFactory):
    class Meta:
        model = ServiceAccount

    class Params:
        plaintext_token = None

    user = SubFactory(UserFactory)
    owner = SubFactory(UploaderIdentityFactory)
    api_token = LazyAttribute(
        lambda o: hash_service_account_api_token(
            o.plaintext_token or get_service_account_api_token()
        )
    )
