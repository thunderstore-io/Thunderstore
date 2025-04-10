import pytest
from django.http import Http404
from rest_framework.exceptions import PermissionDenied

from thunderstore.api.cyberstorm.services import error_messages
from thunderstore.api.cyberstorm.services import team as team_services
from thunderstore.repository.models import Team


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
    with pytest.raises(PermissionDenied, match=error_messages.CANNOT_ACCESS_TEAM):
        team_services.disband_team(user, team.name)


@pytest.mark.django_db
def test_disband_team_user_cannot_disband(team_member):
    with pytest.raises(PermissionDenied, match=error_messages.CANNOT_DISBAND_TEAM):
        team_services.disband_team(team_member.user, team_member.team.name)
