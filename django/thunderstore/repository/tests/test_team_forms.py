from typing import Optional

import pytest
from django.core.exceptions import ValidationError

from conftest import TestUserTypes
from thunderstore.core.factories import UserFactory
from thunderstore.core.types import UserType
from thunderstore.repository.forms import (
    AddTeamMemberForm,
    CreateTeamForm,
    DisbandTeamForm,
    DonationLinkTeamForm,
    EditTeamMemberForm,
    RemoveTeamMemberForm,
    Team,
    TeamMember,
    TeamMemberRole,
)
from thunderstore.repository.models import Package


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
def test_form_create_team_valid_data(user_type: str) -> None:
    error_map = {
        TestUserTypes.no_user: "Must be authenticated to create teams",
        TestUserTypes.unauthenticated: "Must be authenticated to create teams",
        TestUserTypes.regular_user: None,
        TestUserTypes.deactivated_user: "Must be authenticated to create teams",
        TestUserTypes.service_account: "Service accounts cannot create teams",
        TestUserTypes.site_admin: None,
        TestUserTypes.superuser: None,
    }
    expected_error = error_map[user_type]

    user = TestUserTypes.get_user_by_type(user_type)
    form = CreateTeamForm(
        user=user,
        data={"name": "TeamName"},
    )
    if expected_error:
        assert form.is_valid() is False
        assert expected_error in str(repr(form.errors))
    else:
        assert form.is_valid() is True
        team = form.save()
        assert team.name == "TeamName"
        assert team.members.count() == 1
        member = team.members.first()
        assert member.user == user
        assert member.role == TeamMemberRole.owner


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("name1", "name2", "should_fail"),
    (
        ("Team", "team", True),
        ("Team", "t_eam", False),
        ("team", "teaM", True),
        ("team", "team", True),
    ),
)
def test_form_create_team_team_name_conflict(
    user: UserType, name1: str, name2: str, should_fail: True
) -> None:
    Team.create(name=name1)
    form = CreateTeamForm(
        user=user,
        data={"name": name2},
    )
    if should_fail:
        assert form.is_valid() is False
        assert "A team with the provided name already exists" in str(repr(form.errors))
    else:
        assert form.is_valid() is True
        team = form.save()
        assert team.name == name2


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("name", "should_fail"),
    (
        ("Team", False),
        ("Team_Name", False),
        ("Team-Name", True),
        ("Team.Name", True),
        ("_Team", True),
        ("Team_", True),
    ),
)
def test_form_create_team_team_name_validation(
    user: UserType, name: str, should_fail: True
) -> None:
    error = (
        "Author name can only contain a-z A-Z 0-9 _ "
        "characters and must not start or end with _"
    )
    form = CreateTeamForm(
        user=user,
        data={"name": name},
    )
    if should_fail:
        assert form.is_valid() is False
        assert error in str(repr(form.errors))
    else:
        assert form.is_valid() is True
        team = form.save()
        assert team.name == name


@pytest.mark.django_db
@pytest.mark.parametrize("adder_type", TestUserTypes.options())
@pytest.mark.parametrize("added_type", TestUserTypes.options())
@pytest.mark.parametrize("adder_role", TeamMemberRole.options() + [None])
@pytest.mark.parametrize("added_role", TeamMemberRole.options() + [None])
def test_form_add_team_member(
    adder_type: str, added_type: str, adder_role: str, added_role: str
) -> None:
    # TODO: Split to two maps (adder & added) if permissions become asymmetrical
    # Currently validity is symmetrical so a shared map can be used
    user_type_valid_map = {
        TestUserTypes.no_user: False,
        TestUserTypes.unauthenticated: False,
        TestUserTypes.regular_user: True,
        TestUserTypes.deactivated_user: False,
        TestUserTypes.service_account: False,
        TestUserTypes.site_admin: True,
        TestUserTypes.superuser: True,
    }
    adder_type_valid = user_type_valid_map[adder_type] is True
    added_type_valid = user_type_valid_map[added_type] is True

    adder_role_valid_map = {
        None: False,
        TeamMemberRole.member: False,
        TeamMemberRole.owner: True,
    }
    adder_role_valid = adder_role_valid_map[adder_role] is True

    added_role_valid_map = {
        None: False,
        TeamMemberRole.member: True,
        TeamMemberRole.owner: True,
    }
    added_role_valid = added_role_valid_map[added_role] is True

    adder = TestUserTypes.get_user_by_type(adder_type)
    added = TestUserTypes.get_user_by_type(added_type)
    team = Team.create(name="Test")

    if adder is not None and adder.is_authenticated and adder_role is not None:
        TeamMember.objects.create(
            team=team,
            user=adder,
            role=adder_role,
        )

    form = AddTeamMemberForm(
        user=adder,
        data={
            "role": added_role,
            "team": team.pk,
            "user": added.username if added else None,
        },
    )
    should_be_valid = all(
        (adder_type_valid, added_type_valid, adder_role_valid, added_role_valid)
    )
    if should_be_valid:
        assert form.is_valid() is True
        membership = form.save()
        assert membership is not None
        assert membership.team == team
        assert membership.role == added_role
    else:
        assert form.is_valid() is False
        assert form.errors


@pytest.mark.django_db
@pytest.mark.parametrize("remover_type", TestUserTypes.options())
@pytest.mark.parametrize("removed_type", TestUserTypes.options())
@pytest.mark.parametrize("remover_role", TeamMemberRole.options() + [None])
@pytest.mark.parametrize("removed_role", TeamMemberRole.options() + [None])
def test_form_remove_team_member(
    remover_type: str, removed_type: str, remover_role: str, removed_role: str
) -> None:
    remover_type_valid_map = {
        TestUserTypes.no_user: False,
        TestUserTypes.unauthenticated: False,
        TestUserTypes.regular_user: True,
        TestUserTypes.deactivated_user: False,
        TestUserTypes.service_account: False,
        TestUserTypes.site_admin: True,
        TestUserTypes.superuser: True,
    }
    removed_type_valid_map = {
        **remover_type_valid_map,
        **{TestUserTypes.deactivated_user: True},
    }
    remover_role_valid_map = {
        None: False,
        TeamMemberRole.member: False,
        TeamMemberRole.owner: True,
    }
    removed_role_valid_map = {
        None: False,
        TeamMemberRole.member: True,
        TeamMemberRole.owner: True,
    }
    remover_valid = all(
        (
            remover_type_valid_map[remover_type],
            remover_role_valid_map[remover_role],
        )
    )
    removed_valid = all(
        (
            removed_type_valid_map[removed_type],
            removed_role_valid_map[removed_role],
        )
    )

    remover = TestUserTypes.get_user_by_type(remover_type)
    removed = TestUserTypes.get_user_by_type(removed_type)
    team = Team.create(name="Test")

    if remover is not None and remover.is_authenticated and remover_role is not None:
        TeamMember.objects.create(
            team=team,
            user=remover,
            role=remover_role,
        )

    if removed is not None and removed.is_authenticated and removed_role is not None:
        membership = TeamMember.objects.create(
            team=team,
            user=removed,
            role=removed_role,
        ).pk
    else:
        membership = None

    form = RemoveTeamMemberForm(
        user=remover,
        data={"membership": membership},
    )
    should_be_valid = all((remover_valid, removed_valid))
    if should_be_valid:
        assert form.is_valid() is True
        assert form.save() is None
        assert TeamMember.objects.filter(pk=membership).exists() is False
    else:
        with pytest.raises(ValidationError):
            form.save()
        assert form.is_valid() is False
        assert form.errors


@pytest.mark.django_db
@pytest.mark.parametrize("role", TeamMemberRole.options())
def test_form_remove_team_member_works_on_self(role: str) -> None:
    user = UserFactory()
    team = Team.create(name="Test")
    TeamMember.objects.create(
        user=UserFactory(),
        team=team,
        role=TeamMemberRole.owner,
    )
    membership = TeamMember.objects.create(
        user=user,
        team=team,
        role=role,
    )
    form = RemoveTeamMemberForm(
        user=user,
        data={"membership": membership.pk},
    )
    assert form.is_valid() is True
    assert form.save() is None
    assert TeamMember.objects.filter(pk=membership.pk).exists() is False


@pytest.mark.django_db
def test_form_remove_team_member_last_owner() -> None:
    user = UserFactory()
    team = Team.create(name="Test")
    last_owner = TeamMember.objects.create(
        user=user,
        team=team,
        role=TeamMemberRole.owner,
    )
    form = RemoveTeamMemberForm(
        user=user,
        data={"membership": last_owner.pk},
    )
    with pytest.raises(ValidationError):
        form.save()
    assert form.is_valid() is False
    assert "Cannot remove last owner from team" in str(repr(form.errors))


@pytest.mark.django_db
@pytest.mark.parametrize("editor_type", TestUserTypes.options())
@pytest.mark.parametrize("edited_type", TestUserTypes.options())
@pytest.mark.parametrize("editor_role", TeamMemberRole.options() + [None])
@pytest.mark.parametrize("edited_role", TeamMemberRole.options() + [None])
@pytest.mark.parametrize("new_role", TeamMemberRole.options() + [None])
def test_form_edit_team_member(
    editor_type: str,
    edited_type: str,
    editor_role: str,
    edited_role: str,
    new_role: str,
) -> None:
    editor_type_valid_map = {
        TestUserTypes.no_user: False,
        TestUserTypes.unauthenticated: False,
        TestUserTypes.regular_user: True,
        TestUserTypes.deactivated_user: False,
        TestUserTypes.service_account: False,
        TestUserTypes.site_admin: True,
        TestUserTypes.superuser: True,
    }
    edited_type_valid_map = {
        **editor_type_valid_map,
        **{TestUserTypes.deactivated_user: True, TestUserTypes.service_account: True},
    }
    editor_role_valid_map = {
        None: False,
        TeamMemberRole.member: False,
        TeamMemberRole.owner: True,
    }
    edited_role_valid_map = {
        None: False,
        TeamMemberRole.member: True,
        TeamMemberRole.owner: True,
    }
    editor_valid = all(
        (
            editor_type_valid_map[editor_type],
            editor_role_valid_map[editor_role],
        )
    )
    edited_valid = all(
        (
            edited_type_valid_map[edited_type],
            edited_role_valid_map[edited_role],
        )
    )
    new_role_valid = new_role is not None
    is_valid = all((editor_valid, edited_valid, new_role_valid))

    editor = TestUserTypes.get_user_by_type(editor_type)
    edited = TestUserTypes.get_user_by_type(edited_type)
    team = Team.create(name="Test")

    if editor is not None and editor.is_authenticated and editor_role is not None:
        TeamMember.objects.create(
            team=team,
            user=editor,
            role=editor_role,
        )

    if edited is not None and edited.is_authenticated and edited_role is not None:
        membership = TeamMember.objects.create(
            team=team,
            user=edited,
            role=edited_role,
        )
    else:
        membership = None

    form = EditTeamMemberForm(
        user=editor,
        instance=membership,
        data={"role": new_role},
    )
    if is_valid:
        assert form.is_valid() is True
        assert form.save() is membership
        membership.refresh_from_db()
        assert membership.role == new_role
    else:
        with pytest.raises(ValidationError):
            form.save()
        assert form.is_valid() is False
        assert form.errors


@pytest.mark.django_db
def test_form_edit_team_member_remove_last_owner() -> None:
    user = UserFactory()
    team = Team.create(name="Test")
    last_owner = TeamMember.objects.create(
        user=user,
        team=team,
        role=TeamMemberRole.owner,
    )
    form = EditTeamMemberForm(
        user=user,
        instance=last_owner,
        data={"role": TeamMemberRole.member},
    )
    with pytest.raises(ValidationError):
        form.save()
    assert form.is_valid() is False
    assert "Cannot remove last owner from team" in str(repr(form.errors))


@pytest.mark.django_db
@pytest.mark.parametrize("disbander_type", TestUserTypes.options())
@pytest.mark.parametrize("disbander_role", TeamMemberRole.options() + [None])
def test_form_disband_team_form(
    team: Team, disbander_type: str, disbander_role: str
) -> None:
    disbander_type_valid_map = {
        TestUserTypes.no_user: False,
        TestUserTypes.unauthenticated: False,
        TestUserTypes.regular_user: True,
        TestUserTypes.deactivated_user: False,
        TestUserTypes.service_account: False,
        TestUserTypes.site_admin: True,
        TestUserTypes.superuser: True,
    }
    disbander_role_valid_map = {
        None: False,
        TeamMemberRole.member: False,
        TeamMemberRole.owner: True,
    }
    should_succeed = all(
        (
            disbander_type_valid_map[disbander_type],
            disbander_role_valid_map[disbander_role],
        )
    )

    disbander = TestUserTypes.get_user_by_type(disbander_type)
    if (
        disbander is not None
        and disbander.is_authenticated
        and disbander_role is not None
    ):
        TeamMember.objects.create(
            team=team,
            user=disbander,
            role=disbander_role,
        )

    form = DisbandTeamForm(
        user=disbander,
        instance=team,
        data={"verification": team.name},
    )

    if should_succeed:
        assert form.is_valid() is True
        assert form.save() is None
        assert Team.objects.filter(pk=team.pk).exists() is False
    else:
        assert form.is_valid() is False
        assert form.errors


@pytest.mark.django_db
def test_form_disband_team_form_invalid_verification(
    user: UserType, team: Team
) -> None:
    TeamMember.objects.create(
        user=user,
        team=team,
        role=TeamMemberRole.owner,
    )
    form = DisbandTeamForm(
        user=user,
        instance=team,
        data={"verification": f"invalid-{team.name}"},
    )
    assert form.is_valid() is False
    assert "Invalid verification" in str(repr(form.errors))


@pytest.mark.django_db
def test_form_disband_team_form_packages_exist(
    user: UserType, team: Team, package: Package
) -> None:
    TeamMember.objects.create(
        user=user,
        team=team,
        role=TeamMemberRole.owner,
    )
    form = DisbandTeamForm(
        user=user,
        instance=team,
        data={"verification": team.name},
    )
    assert form.is_valid() is False
    assert "Unable to disband teams with packages" in str(repr(form.errors))


@pytest.mark.django_db
def test_form_disband_team_form_no_instance(user: UserType, team: Team) -> None:
    TeamMember.objects.create(
        user=user,
        team=team,
        role=TeamMemberRole.owner,
    )
    form = DisbandTeamForm(
        user=user,
        data={"verification": ""},
    )
    assert form.is_valid() is False
    assert "Missing team instance" in str(repr(form.errors))


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
@pytest.mark.parametrize("role", TeamMemberRole.options() + [None])
def test_form_donation_link_team_form_permissions(
    team: Team, user_type: str, role: str
) -> None:
    # Use 1:1 mapping to ensure the test fails if new roles or user types are added
    valid_user_type_map = {
        TestUserTypes.no_user: False,
        TestUserTypes.unauthenticated: False,
        TestUserTypes.regular_user: True,
        TestUserTypes.deactivated_user: False,
        TestUserTypes.service_account: False,
        TestUserTypes.site_admin: True,
        TestUserTypes.superuser: True,
    }
    valid_role_map = {
        None: False,
        TeamMemberRole.member: False,
        TeamMemberRole.owner: True,
    }
    should_succeed = all(
        (
            valid_user_type_map[user_type],
            valid_role_map[role],
        )
    )

    user = TestUserTypes.get_user_by_type(user_type)
    if role is not None and user_type not in TestUserTypes.fake_users():
        TeamMember.objects.create(user=user, team=team, role=role)

    link = "https://example.org/"
    team.donation_link = None
    team.save()
    team.refresh_from_db()
    assert team.donation_link is None

    form = DonationLinkTeamForm(user=user, instance=team, data={"donation_link": link})
    if should_succeed:
        assert form.is_valid() is True
        assert form.save() is team
        team.refresh_from_db()
        assert team.donation_link == link
    else:
        with pytest.raises(ValidationError):
            form.save()
        assert form.is_valid() is False
        assert form.errors
        team.refresh_from_db()
        assert team.donation_link is None


@pytest.mark.django_db
@pytest.mark.parametrize(
    "value, should_succeed",
    (
        (None, True),
        ("", True),
        ("http://patreon.com/", False),
        ("https://patreon.com/", True),
    ),
)
def test_form_donation_link_team_form_input_validation(
    team: Team,
    user: UserType,
    value: Optional[str],
    should_succeed: bool,
) -> None:
    TeamMember.objects.create(
        user=user,
        team=team,
        role=TeamMemberRole.owner,
    )
    form = DonationLinkTeamForm(
        user=user,
        instance=team,
        data={"donation_link": value},
    )
    assert form.is_valid() is should_succeed
    if should_succeed:
        assert not form.errors
    else:
        assert "Enter a valid URL." in str(repr(form.errors))


@pytest.mark.django_db
def test_form_donation_link_team_form_no_instance(
    team: Team,
    user: UserType,
) -> None:
    TeamMember.objects.create(
        user=user,
        team=team,
        role=TeamMemberRole.owner,
    )
    form = DonationLinkTeamForm(
        user=user,
        data={"donation_link": None},
    )
    assert form.is_valid() is False
    assert "Missing team instance" in str(repr(form.errors))
