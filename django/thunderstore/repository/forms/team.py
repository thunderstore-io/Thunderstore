from typing import Optional

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction

from thunderstore.api.cyberstorm.services.team import (
    create_team,
    disband_team,
    remove_team_member,
    update_team,
    update_team_member,
)
from thunderstore.core.types import UserType
from thunderstore.repository.models import Team, TeamMember, TeamMemberRole
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

    def clean_name(self):
        name = self.cleaned_data["name"]
        if Team.objects.filter(name__iexact=name).exists():
            raise ValidationError("Team with this name already exists")
        return name

    @transaction.atomic
    def save(self, *args, **kwargs) -> Team:
        if self.errors:
            raise ValidationError(self.errors)

        try:
            team_name = self.cleaned_data["name"]
            instance = create_team(agent=self.user, team_name=team_name)
        except ValidationError as e:
            self.add_error(None, e)
            raise ValidationError(self.errors)

        return instance


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

    def save(self):
        if self.errors:
            raise ValidationError(self.errors)

        member = self.cleaned_data["membership"]

        try:
            remove_team_member(agent=self.user, member=member)
        except ValidationError as e:
            self.add_error(None, e)
            raise ValidationError(self.errors)


class EditTeamMemberForm(forms.ModelForm):
    class Meta:
        model = TeamMember
        fields = ["role"]

    def __init__(self, user: Optional[UserType], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean(self):
        if not self.instance.pk:
            raise ValidationError("Missing team member instance")

        try:
            self.instance.team
        except ObjectDoesNotExist:
            raise ValidationError("Team is missing")

        return super().clean()

    def save(self, *args, **kwargs):
        if self.errors:
            raise ValidationError(self.errors)

        try:
            update_team_member(
                agent=self.user,
                team_member=self.instance,
                role=self.cleaned_data["role"],
            )
        except ValidationError as e:
            self.add_error(None, e)
            raise ValidationError(self.errors)

        return self.instance


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
        data = self.cleaned_data["verification"]
        if data != self.instance.name:
            raise forms.ValidationError("Invalid verification")
        return data

    def clean(self):
        if not self.instance.pk:
            raise ValidationError("Missing team instance")
        return super().clean()

    @transaction.atomic
    def save(self, **kwargs):
        if self.errors:
            raise ValidationError(self.errors)
        try:
            disband_team(agent=self.user, team=self.instance)
        except ValidationError as e:
            self.add_error(None, e)
            raise ValidationError(self.errors)


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
        return super().clean()

    @transaction.atomic
    def save(self, **kwargs):
        if self.errors:
            raise ValidationError(self.errors)

        try:
            update_team(
                agent=self.user,
                team=self.instance,
                donation_link=self.cleaned_data["donation_link"],
            )
        except ValidationError as e:
            self.add_error(None, e)
            raise ValidationError(self.errors)

        return self.instance
