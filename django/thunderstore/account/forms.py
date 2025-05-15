from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction

from thunderstore.account.models import ServiceAccount
from thunderstore.api.cyberstorm.services.team import (
    create_service_account,
    delete_service_account,
)
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

    @transaction.atomic
    def save(self) -> ServiceAccount:
        if self.errors:
            raise ValueError("Cannot save form with errors")

        self.api_token = ""

        owner = self.cleaned_data["team"]
        nickname = self.cleaned_data["nickname"]
        service_account = None

        try:
            service_account, token = create_service_account(
                agent=self.user,
                team=owner,
                nickname=nickname,
            )
            self.api_token = token
            service_account = service_account
        except ValidationError as e:
            self.add_error(None, e)

        return service_account


class DeleteServiceAccountForm(forms.Form):
    def __init__(self, user: UserType, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["service_account"] = forms.ModelChoiceField(
            queryset=ServiceAccount.objects.filter(owner__members__user=user),
        )

    def save(self) -> None:
        if self.errors:
            raise ValueError("Cannot save form with errors")

        service_account = self.cleaned_data["service_account"]

        try:
            delete_service_account(self.user, service_account)
        except ValidationError as e:
            self.add_error(None, e)


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
