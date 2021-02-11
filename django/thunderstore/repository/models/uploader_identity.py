from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction

from thunderstore.core.utils import ChoiceEnum
from thunderstore.repository.validators import AuthorNameRegexValidator


class UploaderIdentityMemberRole(ChoiceEnum):
    owner = "owner"
    member = "member"


class UploaderIdentityMember(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="uploader_identities",
        on_delete=models.CASCADE,
    )
    identity = models.ForeignKey(
        "repository.UploaderIdentity",
        related_name="members",
        on_delete=models.CASCADE,
    )
    role = models.CharField(
        max_length=64,
        default=UploaderIdentityMemberRole.member,
        choices=UploaderIdentityMemberRole.as_choices(),
    )

    class Meta:
        unique_together = ("user", "identity")
        verbose_name = "Uploader Identity Member"
        verbose_name_plural = "Uploader Identy Members"

    def __str__(self):
        return f"{self.user.username} membership to {self.identity.name}"


class UploaderIdentity(models.Model):

    name = models.CharField(
        max_length=64,
        unique=True,
        validators=[AuthorNameRegexValidator],
    )

    class Meta:
        verbose_name = "Uploader Identity"
        verbose_name_plural = "Uploader Identities"

    def __str__(self):
        return self.name

    def validate(self):
        for validator in self._meta.get_field("name").validators:
            validator(self.name)

    def save(self, *args, **kwargs):
        self.validate()
        return super().save(*args, **kwargs)

    @classmethod
    @transaction.atomic
    def get_or_create_for_user(cls, user):
        identity_membership = user.uploader_identities.first()
        if identity_membership:
            return identity_membership.identity

        identity, created = cls.objects.get_or_create(
            name=user.username,
        )
        if created:
            UploaderIdentityMember.objects.create(
                user=user,
                identity=identity,
                role=UploaderIdentityMemberRole.owner,
            )
        if not identity.members.filter(user=user).exists():
            raise RuntimeError("User missing permissions")
        return identity

    def can_user_upload(self, user):
        membership = self.members.filter(user=user).first()
        if not membership:
            return False
        return membership.role in (
            UploaderIdentityMemberRole.owner,
            UploaderIdentityMemberRole.member,
        )

    def ensure_can_create_service_account(self, user) -> None:
        membership = self.members.filter(user=user).first()
        if not membership:
            raise ValidationError("Must be a member to create a service account")
        if membership.role != UploaderIdentityMemberRole.owner:
            raise ValidationError("Must be an owner to create a service account")

    def ensure_can_edit_service_account(self, user) -> None:
        membership = self.members.filter(user=user).first()
        if not membership:
            raise ValidationError("Must be a member to edit a service account")
        if membership.role != UploaderIdentityMemberRole.owner:
            raise ValidationError("Must be an owner to edit a service account")

    def ensure_can_delete_service_account(self, user) -> None:
        membership = self.members.filter(user=user).first()
        if not membership:
            raise ValidationError("Must be a member to delete a service account")
        if membership.role != UploaderIdentityMemberRole.owner:
            raise ValidationError("Must be an owner to delete a service account")

    def ensure_can_generate_service_account_token(self, user) -> None:
        membership = self.members.filter(user=user).first()
        if not membership:
            raise ValidationError(
                "Must be a member to generate a service account token",
            )
        if membership.role != UploaderIdentityMemberRole.owner:
            raise ValidationError(
                "Must be an owner to generate a service account token",
            )
