from django.db import transaction

from thunderstore.account.models import ServiceAccount
from thunderstore.core.types import UserType
from thunderstore.repository.models import Team


@transaction.atomic
def create_service_account(agent: UserType, team: Team, nickname: str):
    team.ensure_user_can_access(agent)
    team.ensure_can_create_service_account(agent)

    service_account, token = ServiceAccount.create(
        owner=team,
        nickname=nickname,
        creator=agent,
    )

    return service_account, token


@transaction.atomic
def delete_service_account(agent: UserType, service_account: ServiceAccount):
    team = service_account.owner
    team.ensure_user_can_access(agent)
    team.ensure_can_delete_service_account(agent)
    return service_account.delete()
