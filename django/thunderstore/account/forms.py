from django import forms
from django.db import transaction

from thunderstore.account.models import ServiceAccount
from thunderstore.core.exceptions import PermissionValidationError
from thunderstore.core.types import UserType
from thunderstore.repository.models import Team


class CreateServiceAccountForm(forms.Form):
    nickname = forms.CharField(max_length=32)

    def __init__(self, user: UserType, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["team"] = forms.ModelChoiceField(
            queryset=Team.objects.filter(members__user=user, is_active=True),
        )

    def clean_team(self) -> Team:
        team = self.cleaned_data["team"]
        errors, _ = team.validate_can_create_service_account(self.user)
        if errors:
            raise forms.ValidationError(errors)
        return team

    @transaction.atomic
    def save(self) -> ServiceAccount:
        owner = self.cleaned_data["team"]
        nickname = self.cleaned_data["nickname"]
        (service_account, token) = ServiceAccount.create(
            owner=owner, nickname=nickname, creator=self.user
        )
        self.api_token = token
        return service_account


class DeleteServiceAccountForm(forms.Form):
    def __init__(self, user: UserType, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["service_account"] = forms.ModelChoiceField(
            queryset=ServiceAccount.objects.filter(owner__members__user=user),
        )

    def clean_service_account(self) -> ServiceAccount:
        service_account = self.cleaned_data["service_account"]
        errors, is_public = service_account.owner.validate_can_delete_service_account(
            self.user
        )
        if errors:
            raise PermissionValidationError(errors, is_public=is_public)
        return service_account

    def save(self) -> None:
        self.cleaned_data["service_account"].delete()


class EditServiceAccountForm(forms.Form):
    nickname = forms.CharField(max_length=32)

    def __init__(self, user: UserType, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["service_account"] = forms.ModelChoiceField(
            queryset=ServiceAccount.objects.filter(owner__members__user=user),
        )

    def clean_service_account(self) -> ServiceAccount:
        service_account = self.cleaned_data["service_account"]
        errors, is_public = service_account.owner.validate_can_edit_service_account(
            self.user
        )
        if errors:
            raise PermissionValidationError(errors, is_public=is_public)
        return service_account

    def save(self) -> ServiceAccount:
        service_account = self.cleaned_data["service_account"]
        service_account.user.first_name = self.cleaned_data["nickname"]
        service_account.user.save(update_fields=("first_name",))
        return service_account
