import ulid2
from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from thunderstore.account.models import ServiceAccount
from thunderstore.repository.models import UploaderIdentity


def create_service_account_username(id_: str) -> str:
    return f"{id_}.sa@thunderstore.io"


class CreateServiceAccountForm(forms.Form):
    nickname = forms.CharField(max_length=32)

    def __init__(self, user: User, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["identity"] = forms.ModelChoiceField(
            queryset=UploaderIdentity.objects.filter(members__user=user),
        )

    def clean_identity(self) -> UploaderIdentity:
        identity = self.cleaned_data["identity"]
        if not identity.can_create_service_account(self.user):
            raise ValidationError("Must be identity owner to create a service account")
        return identity

    def clean(self) -> None:
        super().clean()
        nickname = self.cleaned_data.get("nickname")
        identity = self.cleaned_data.get("identity")

        if not all((nickname, identity)):
            return

    def save(self) -> ServiceAccount:
        service_account_id = ulid2.generate_ulid_as_uuid()
        username = create_service_account_username(service_account_id.hex)
        user = User.objects.create_user(
            username,
            email=username,
            first_name=self.cleaned_data["nickname"],
        )
        return ServiceAccount.objects.create(
            uuid=service_account_id,
            user=user,
            owner=self.cleaned_data["identity"],
        )


class DeleteServiceAccountForm(forms.Form):
    def __init__(self, user: User, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["service_account"] = forms.ModelChoiceField(
            queryset=ServiceAccount.objects.filter(owner__members__user=user),
        )

    def clean_service_account(self) -> ServiceAccount:
        service_account = self.cleaned_data["service_account"]
        if not service_account.owner.can_delete_service_account(self.user):
            raise ValidationError("Must be identity owner to delete a service account")
        return service_account

    def save(self) -> None:
        self.cleaned_data["service_account"].delete()


class EditServiceAccountForm(forms.Form):
    nickname = forms.CharField(max_length=32)

    def __init__(self, user: User, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["service_account"] = forms.ModelChoiceField(
            queryset=ServiceAccount.objects.filter(owner__members__user=user),
        )

    def clean_service_account(self) -> ServiceAccount:
        service_account = self.cleaned_data["service_account"]
        if not service_account.owner.can_edit_service_account(self.user):
            raise ValidationError("Must be identity owner to edit a service account")
        return service_account

    def clean(self) -> None:
        super().clean()
        nickname = self.cleaned_data.get("nickname")
        service_account = self.cleaned_data.get("service_account")

        if not all((nickname, service_account)):
            return

    def save(self) -> ServiceAccount:
        service_account = self.cleaned_data["service_account"]
        service_account.user.first_name = self.cleaned_data["nickname"]
        service_account.save()
        return service_account
