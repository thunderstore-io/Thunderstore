from typing import Optional

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError

from thunderstore.core.exceptions import PermissionValidationError
from thunderstore.core.types import UserType
from thunderstore.repository.models import (
    Namespace,
    Team,
    TeamMember,
    TeamMemberRole,
    transaction,
)
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
        if Team.objects.filter(name__iexact=name.lower()).exists():
            raise ValidationError(f"A team with the provided name already exists")
        if Namespace.objects.filter(name__iexact=name.lower()).exists():
            raise ValidationError("A namespace with the provided name already exists")
        return name

    def clean(self):
        if not self.user or not self.user.is_authenticated or not self.user.is_active:
            raise PermissionValidationError("Must be authenticated to create teams")
        if getattr(self.user, "service_account", None) is not None:
            raise PermissionValidationError("Service accounts cannot create teams")
        return super().clean()

    @transaction.atomic
    def save(self, *args, **kwargs) -> Team:
        instance = super().save()
        instance.add_member(user=self.user, role=TeamMemberRole.owner)
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
        data = self.cleaned_data["verification"]
        if data != self.instance.name:
            raise forms.ValidationError("Invalid verification")
        return data

    def clean(self):
        if not self.instance.pk:
            raise ValidationError("Missing team instance")
        self.instance.ensure_user_can_disband(self.user)
        return super().clean()

    @transaction.atomic
    def save(self, **kwargs):
        self.instance.ensure_user_can_disband(self.user)
        self.instance.delete()


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
