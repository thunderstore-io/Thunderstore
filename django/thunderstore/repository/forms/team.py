from typing import Optional

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError

from thunderstore.api.cyberstorm.services.team import create_team, disband_team
from thunderstore.core.types import UserType
from thunderstore.repository.models import Team, TeamMember, TeamMemberRole, transaction
from thunderstore.repository.validators import PackageReferenceComponentValidator

User = get_user_model()


class CreateTeamForm(forms.ModelForm):
    name = forms.CharField(
        validators=[PackageReferenceComponentValidator("Author name")]
    )

    class Meta:
        model = Team
        fields = ["name"]

    def __init__(self, user: UserType, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    @transaction.atomic
    def save(self, *args, **kwargs) -> Team:
        if self.errors:
            raise ValueError("Form has errors")

        try:
            team_name = self.cleaned_data["name"]
            self.instance = create_team(agent=self.user, team_name=team_name)
        except ValidationError as e:
            self.add_error(None, e)

        return self.instance


class AddTeamMemberForm(forms.ModelForm):
    user = forms.ModelChoiceField(
        queryset=(User.objects.filter(service_account=None, is_active=True)),
        to_field_name="username",
    )
    user: Optional[UserType]

    class Meta:
        model = TeamMember
        fields = ["role", "team", "user"]

    def __init__(self, user: Optional[UserType], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user is not None and user.is_authenticated:
            team_qs = Team.objects.filter(members__user=user)
        else:
            team_qs = Team.objects.none()
        self.fields["team"] = forms.ModelChoiceField(
            queryset=team_qs,
        )
        self.fields["role"].initial = TeamMemberRole.member

    def clean(self):
        result = super().clean()
        team = self.cleaned_data.get("team")
        if team:
            team.ensure_user_can_manage_members(self.user)
        else:
            raise ValidationError("Invalid team")
        return result


class RemoveTeamMemberForm(forms.Form):
    membership = forms.ModelChoiceField(TeamMember.objects.real_users(), required=True)

    def __init__(self, user: Optional[UserType], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_membership(self):
        membership = self.cleaned_data["membership"]
        if membership.user != self.user:
            membership.team.ensure_user_can_manage_members(self.user)
        membership.team.ensure_member_can_be_removed(membership)
        return membership

    def save(self):
        self.cleaned_data["membership"].delete()


class EditTeamMemberForm(forms.ModelForm):
    class Meta:
        model = TeamMember
        fields = ["role"]

    def __init__(self, user: Optional[UserType], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_role(self):
        new_role = self.cleaned_data.get("role", None)
        try:
            team = self.instance.team
        except ObjectDoesNotExist:
            team = None
        if team:
            team.ensure_member_role_can_be_changed(
                member=self.instance, new_role=new_role
            )
        else:
            raise ValidationError("Team is missing")
        return new_role

    def clean(self):
        try:
            team = self.instance.team
        except ObjectDoesNotExist:
            team = None
        if team:
            team.ensure_user_can_manage_members(self.user)
        else:
            raise ValidationError("Team is missing")
        return super().clean()


class DisbandTeamForm(forms.ModelForm):
    verification = forms.CharField()
    instance: Team

    class Meta:
        model = Team
        fields = []

    def __init__(self, user: UserType, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_verification(self):
        verification = self.cleaned_data["verification"]
        if verification != self.instance.name:
            raise forms.ValidationError("Invalid verification")
        return verification

    def clean(self):
        if not self.instance.pk:
            raise ValidationError("Missing team instance")
        return super().clean()

    def save(self, **kwargs):
        if self.errors:
            raise ValueError("Form has errors")

        try:
            disband_team(agent=self.user, team=self.instance)
        except ValidationError as e:
            self.add_error(None, e)


class DonationLinkTeamForm(forms.ModelForm):
    instance: Team

    class Meta:
        model = Team
        fields = ["donation_link"]

    def __init__(self, user: UserType, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean(self):
        if not self.instance.pk:
            raise ValidationError("Missing team instance")
        self.instance.ensure_user_can_edit_info(self.user)
        return super().clean()

    @transaction.atomic
    def save(self, **kwargs):
        self.instance.ensure_user_can_edit_info(self.user)
        return super().save(**kwargs)
