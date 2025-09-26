import pytest
from django.core.exceptions import ValidationError
from django.http import Http404

from conftest import TestUserTypes
from thunderstore.api.cyberstorm.services import team as team_services
from thunderstore.core.exceptions import PermissionValidationError
from thunderstore.repository.models import Namespace, Team, TeamMemberRole
from thunderstore.repository.models.team import TeamMember


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
def test_update_team_success(team_owner):
    team = team_owner.team
    new_donation_link = "https://example.com/donate"
    updated_team = team_services.update_team(
        agent=team_owner.user, team=team, donation_link=new_donation_link
    )

    assert updated_team.donation_link == new_donation_link


@pytest.mark.django_db
def test_update_team_user_cannot_access(user, team):
    new_donation_link = "https://example.com/donate"

    error_msg = "Must be a member to access team"
    with pytest.raises(PermissionValidationError, match=error_msg):
        team_services.update_team(
            agent=user, team=team, donation_link=new_donation_link
        )


@pytest.mark.django_db
def test_update_team_user_cannot_edit_info(team_member):
    new_donation_link = "https://example.com/donate"

    error_msg = "Must be an owner to edit team info"
    with pytest.raises(PermissionValidationError, match=error_msg):
        team_services.update_team(
            agent=team_member.user,
            team=team_member.team,
            donation_link=new_donation_link,
        )


@pytest.mark.django_db
def test_remove_team_member_success(team_owner, user):
    """Owner removes another member successfully."""

    team = team_owner.team
    team.add_member(user=user, role=TeamMemberRole.member)

    member = TeamMember.objects.get(team=team_owner.team, user=user)
    team_services.remove_team_member(agent=team_owner.user, member=member)

    assert not TeamMember.objects.filter(pk=member.pk).exists()


@pytest.mark.django_db
def test_remove_team_member_remove_self(team_member):
    """A member removes themselves from the team successfully."""

    member = TeamMember.objects.get(team=team_member.team, user=team_member.user)
    team_services.remove_team_member(agent=team_member.user, member=member)

    assert not TeamMember.objects.filter(pk=member.pk).exists()


@pytest.mark.django_db
def test_remove_team_member_user_cannot_manage_members(user, team_owner):
    """A non-owner user tries to remove another member."""

    team = team_owner.team
    team.add_member(user=user, role=TeamMemberRole.member)
    member = TeamMember.objects.get(team=team_owner.team, user=team_owner.user)

    error_msg = "Must be an owner to manage team members"
    with pytest.raises(PermissionValidationError, match=error_msg):
        team_services.remove_team_member(agent=user, member=member)


@pytest.mark.django_db
def test_remove_team_member_cannot_remove_last_owner(team_owner):
    """Owner tries to remove themselves when they are the last owner."""

    team = team_owner.team
    member = TeamMember.objects.get(team=team, user=team_owner.user)

    error_msg = "Cannot remove last owner from team"
    with pytest.raises(PermissionValidationError, match=error_msg):
        team_services.remove_team_member(agent=team_owner.user, member=member)


@pytest.mark.django_db
def test_remove_team_member_from_another_team(team_owner, user):
    """An owner tries to remove a member from another team."""

    another_team = Team.objects.create(name="AnotherTeam")
    another_team.add_member(user=user, role=TeamMemberRole.member)
    another_team_member = TeamMember.objects.get(team=another_team, user=user)

    error_msg = "Must be an owner to manage team members"
    with pytest.raises(PermissionValidationError, match=error_msg):
        team_services.remove_team_member(
            agent=team_owner.user, member=another_team_member
        )
