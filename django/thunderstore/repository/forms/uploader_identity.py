from typing import Optional

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError

from thunderstore.core.types import UserType
from thunderstore.repository.models import (
    UploaderIdentity,
    UploaderIdentityMember,
    UploaderIdentityMemberRole,
    transaction,
)
from thunderstore.repository.validators import PackageReferenceComponentValidator

User = get_user_model()


class CreateUploaderIdentityForm(forms.ModelForm):
    name = forms.CharField(
        validators=[PackageReferenceComponentValidator("Author name")]
    )

    class Meta:
        model = UploaderIdentity
        fields = ["name"]

    def __init__(self, user: UserType, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_name(self):
        name = self.cleaned_data["name"]
        if UploaderIdentity.objects.filter(name__iexact=name.lower()).exists():
            raise ValidationError(f"A team with the provided name already exists")
        return name

    def clean(self):
        if not self.user or not self.user.is_authenticated or not self.user.is_active:
            raise ValidationError("Must be authenticated to create teams")
        if getattr(self.user, "service_account", None) is not None:
            raise ValidationError("Service accounts cannot create teams")
        return super().clean()

    @transaction.atomic
    def save(self, *args, **kwargs) -> UploaderIdentity:
        instance = super().save()
        instance.add_member(user=self.user, role=UploaderIdentityMemberRole.owner)
        return instance


class AddUploaderIdentityMemberForm(forms.ModelForm):
    user = forms.ModelChoiceField(
        queryset=(User.objects.filter(service_account=None, is_active=True)),
        to_field_name="username",
    )
    user: Optional[UserType]

    class Meta:
        model = UploaderIdentityMember
        fields = ["role", "identity", "user"]

    def __init__(self, user: Optional[UserType], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user is not None and user.is_authenticated:
            identity_qs = UploaderIdentity.objects.filter(members__user=user)
        else:
            identity_qs = UploaderIdentity.objects.none()
        self.fields["identity"] = forms.ModelChoiceField(
            queryset=identity_qs,
        )
        self.fields["role"].initial = UploaderIdentityMemberRole.member

    def clean(self):
        result = super().clean()
        identity = self.cleaned_data.get("identity")
        if identity:
            identity.ensure_user_can_manage_members(self.user)
        else:
            raise ValidationError("Invalid uploader identity")
        return result


class RemoveUploaderIdentityMemberForm(forms.Form):
    membership = forms.ModelChoiceField(
        UploaderIdentityMember.objects.real_users(), required=True
    )

    def __init__(self, user: Optional[UserType], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_membership(self):
        membership = self.cleaned_data["membership"]
        if membership.user != self.user:
            membership.identity.ensure_user_can_manage_members(self.user)
        membership.identity.ensure_member_can_be_removed(membership)
        return membership

    def save(self):
        self.cleaned_data["membership"].delete()


class EditUploaderIdentityMemberForm(forms.ModelForm):
    class Meta:
        model = UploaderIdentityMember
        fields = ["role"]

    def __init__(self, user: Optional[UserType], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_role(self):
        new_role = self.cleaned_data.get("role", None)
        try:
            identity = self.instance.identity
        except ObjectDoesNotExist:
            identity = None
        if identity:
            identity.ensure_member_role_can_be_changed(
                member=self.instance, new_role=new_role
            )
        else:
            raise ValidationError("Uploader Identity is missing")
        return new_role

    def clean(self):
        try:
            identity = self.instance.identity
        except ObjectDoesNotExist:
            identity = None
        if identity:
            identity.ensure_user_can_manage_members(self.user)
        else:
            raise ValidationError("Uploader Identity is missing")
        return super().clean()


class DisbandUploaderIdentityForm(forms.ModelForm):
    verification = forms.CharField()
    instance: UploaderIdentity

    class Meta:
        model = UploaderIdentity
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
            raise ValidationError("Missing uploader identity instance")
        self.instance.ensure_user_can_disband(self.user)
        return super().clean()

    @transaction.atomic
    def save(self, **kwargs):
        self.instance.ensure_user_can_disband(self.user)
        self.instance.delete()
