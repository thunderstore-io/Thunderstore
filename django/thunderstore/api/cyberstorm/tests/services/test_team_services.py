import pytest
from django.core.exceptions import ValidationError
from django.http import Http404

from thunderstore.api.cyberstorm.services import team as team_services
from thunderstore.repository.models import Namespace, Team, TeamMemberRole


@pytest.mark.django_db
def test_disband_team_success(team_owner):
    team_pk = team_owner.team.pk
    team_services.disband_team(team_owner.user, team_owner.team.name)
    assert not Team.objects.filter(pk=team_pk).exists()


@pytest.mark.django_db
def test_disband_team_team_not_found(user):
    with pytest.raises(Http404):
        team_services.disband_team(user, "NonExistentTeam")


@pytest.mark.django_db
def test_disband_team_user_cannot_access_team(user):
    team = Team.objects.create(name="TestTeam")
    with pytest.raises(ValidationError, match="Must be a member to access team"):
        team_services.disband_team(user, team.name)


@pytest.mark.django_db
def test_disband_team_user_cannot_disband(team_member):
    with pytest.raises(ValidationError, match="Must be an owner to disband team"):
        team_services.disband_team(team_member.user, team_member.team.name)


@pytest.mark.django_db
def test_disband_team_with_packages(package, team_owner):
    team = team_owner.team
    package.owner = team
    package.save()

    with pytest.raises(ValidationError, match="Unable to disband teams with packages"):
        team_services.disband_team(team_owner.user, team.name)


@pytest.mark.django_db
def test_disband_team_user_is_service_account(service_account, team):
    service_account_user = service_account.user
    with pytest.raises(
        ValidationError, match="Service accounts are unable to perform this action"
    ):
        team_services.disband_team(service_account_user, team.name)


@pytest.mark.django_db
def test_disband_team_user_not_authenticated(team):
    with pytest.raises(ValidationError, match="Must be authenticated"):
        team_services.disband_team(None, team.name)


@pytest.mark.django_db
def test_disband_team_user_not_active(user, team):
    user.is_active = False
    user.save()

    with pytest.raises(ValidationError, match="User has been deactivated"):
        team_services.disband_team(user, team.name)


@pytest.mark.django_db
def test_create_team_name_exists_in_team(user):
    Team.objects.create(name="existing_team")

    error_msg = "A team with the provided name already exists"
    with pytest.raises(ValidationError, match=error_msg):
        team_services.create_team(user, "existing_team")


@pytest.mark.django_db
def test_create_team_name_exists_in_namespace(user):
    Namespace.objects.create(name="existing_namespace")

    error_msg = "A namespace with the provided name already exists"
    with pytest.raises(ValidationError, match=error_msg):
        team_services.create_team(user, "existing_namespace")


@pytest.mark.django_db
def test_create_team_user_is_service_account(service_account):
    service_account_user = service_account.user

    error_msg = "Service accounts cannot create teams"
    with pytest.raises(ValidationError, match=error_msg):
        team_services.create_team(service_account_user, "new_team")


@pytest.mark.django_db
def test_create_team_success(user):
    team_name = "new_team"
    team = team_services.create_team(user, team_name)

    assert Team.objects.filter(name=team_name).exists()
    assert team.name == team_name
    assert team.members.filter(user=user, role=TeamMemberRole.owner).exists()


@pytest.mark.django_db
def test_create_team_user_not_authenticated():
    error_msg = "Must be authenticated to create teams"
    with pytest.raises(ValidationError, match=error_msg):
        team_services.create_team(None, "new_team")


@pytest.mark.django_db
def test_create_team_user_not_active(user):
    user.is_active = False
    user.save()

    error_msg = "Must be authenticated to create teams"
    with pytest.raises(ValidationError, match=error_msg):
        team_services.create_team(user, "new_team")
