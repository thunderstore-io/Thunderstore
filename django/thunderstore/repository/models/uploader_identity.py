from django.conf import settings
from django.db import models, transaction
from django.core.exceptions import ValidationError

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
    def get_or_create_for_user(cls, name: str, user) -> "UploaderIdentity":
        uploader_identity, created = cls.objects.get_or_create(name=name)
        if created is True:
            UploaderIdentityMember.objects.create(
                user=user,
                identity=uploader_identity,
                role=UploaderIdentityMemberRole.owner,
            )
        else:
            if uploader_identity.members.filter(user=user).exists() is False:
                raise ValidationError("Not a member of the team")
        return uploader_identity

    def can_user_upload(self, user):
        membership = self.members.filter(user=user).first()
        if not membership:
            return False
        return membership.role in (
            UploaderIdentityMemberRole.owner,
            UploaderIdentityMemberRole.member,
        )
