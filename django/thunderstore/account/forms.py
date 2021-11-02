from django import forms
from django.db import transaction

from thunderstore.account.models import ServiceAccount
from thunderstore.core.types import UserType
from thunderstore.repository.models import Team


class CreateServiceAccountForm(forms.Form):
    nickname = forms.CharField(max_length=32)

    def __init__(self, user: UserType, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["team"] = forms.ModelChoiceField(
            queryset=Team.objects.filter(members__user=user),
        )

    def clean_team(self) -> Team:
        team = self.cleaned_data["team"]
        team.ensure_can_create_service_account(self.user)
        return team

    @transaction.atomic
    def save(self) -> ServiceAccount:
        owner = self.cleaned_data["team"]
        nickname = self.cleaned_data["nickname"]
        (service_account, token) = ServiceAccount.create(owner, nickname)
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
        service_account.owner.ensure_can_delete_service_account(self.user)
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
        service_account.owner.ensure_can_edit_service_account(self.user)
        return service_account

    def save(self) -> ServiceAccount:
        service_account = self.cleaned_data["service_account"]
        service_account.user.first_name = self.cleaned_data["nickname"]
        service_account.user.save(update_fields=("first_name",))
        return service_account
