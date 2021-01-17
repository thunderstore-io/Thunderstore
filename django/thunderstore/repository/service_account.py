import ulid2
from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from thunderstore.repository.models import (
    ServiceAccountMetadata,
    UploaderIdentity,
    UploaderIdentityMemberRole,
)


class CreateServiceAccountForm(forms.Form):
    def __init__(self, user: User, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["identity"] = forms.ModelChoiceField(
            queryset=UploaderIdentity.objects.filter(members__user=user),
        )

    def clean_identity(self) -> UploaderIdentity:
        identity = self.cleaned_data["identity"]
        member = identity.members.get(user=self.user)
        if member.role != UploaderIdentityMemberRole.owner:
            raise ValidationError("Must be identity owner to create a service account")
        return identity

    def save(self) -> ServiceAccountMetadata:
        service_account_id = ulid2.generate_ulid_as_uuid()
        user = User.objects.create_user(service_account_id.hex)
        return ServiceAccountMetadata.objects.create(
            uuid=service_account_id,
            user=user,
            is_service_account=True,
            owner=self.cleaned_data["identity"],
        )


class DeleteServiceAccountForm(forms.Form):
    def __init__(self, user: User, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["service_account"] = forms.ModelChoiceField(
            queryset=ServiceAccountMetadata.objects.filter(
                owner__in=UploaderIdentity.objects.filter(members__user=user),
            ),
        )

    def clean_service_account(self) -> ServiceAccountMetadata:
        service_account = self.cleaned_data["service_account"]
        member = service_account.owner.members.get(user=self.user)
        if member.role != UploaderIdentityMemberRole.owner:
            raise ValidationError("Must be identity owner to delete a service account")
        return service_account

    def save(self) -> None:
        self.cleaned_data["service_account"].delete()
