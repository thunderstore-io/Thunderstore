from typing import Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Manager, Q, QuerySet
from django.urls import reverse

from thunderstore.core.types import UserType
from thunderstore.core.utils import ChoiceEnum, check_validity
from thunderstore.repository.models import Package
from thunderstore.repository.validators import AuthorNameRegexValidator


class UploaderIdentityMemberRole(ChoiceEnum):
    owner = "owner"
    member = "member"


class UploaderIdentityMemberManager(models.Manager):
    def real_users(self) -> "QuerySet[UploaderIdentityMember]":  # TODO: Generic type
        return self.exclude(~Q(user__service_account=None))

    def service_accounts(
        self,
    ) -> "QuerySet[UploaderIdentityMember]":  # TODO: Generic type
        return self.exclude(user__service_account=None)


class UploaderIdentityMember(models.Model):
    objects: "UploaderIdentityMemberManager[UploaderIdentityMemberManager]" = (
        UploaderIdentityMemberManager()
    )

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

    @property
    def can_be_demoted(self):
        return self.role == UploaderIdentityMemberRole.owner

    @property
    def can_be_promoted(self):
        return self.role == UploaderIdentityMemberRole.member

    def __str__(self):
        return f"{self.user.username} membership to {self.identity.name}"


class UploaderIdentity(models.Model):
    objects: "Manager[UploaderIdentity]"
    members: "UploaderIdentityMemberManager[UploaderIdentityMember]"
    owned_packages: "Manager[Package]"

    name = models.CharField(
        max_length=64,
        unique=True,
        validators=[AuthorNameRegexValidator],
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Uploader Identity"
        verbose_name_plural = "Uploader Identities"

    def __str__(self):
        return self.name

    def validate(self):
        for validator in self._meta.get_field("name").validators:
            validator(self.name)
        if not self.pk:
            if UploaderIdentity.objects.filter(name__iexact=self.name.lower()).exists():
                raise ValidationError("The author name already exists")

    def save(self, *args, **kwargs):
        self.validate()
        return super().save(*args, **kwargs)

    @property
    def member_count(self):
        return self.members.count()

    @property
    def settings_url(self):
        return reverse(
            "settings.teams.detail",
            kwargs={"name": self.name},
        )

    def add_member(self, user: UserType, role: str) -> UploaderIdentityMember:
        return UploaderIdentityMember.objects.create(
            identity=self,
            user=user,
            role=role,
        )

    @classmethod
    @transaction.atomic
    def get_or_create_for_user(cls, user: UserType):
        identity_membership = user.uploader_identities.first()
        if identity_membership:
            return identity_membership.identity

        identity, created = cls.objects.get_or_create(
            name=user.username,
        )
        if created:
            identity.add_member(user=user, role=UploaderIdentityMemberRole.owner)
        if not identity.members.filter(user=user).exists():
            raise RuntimeError("User missing permissions")
        return identity

    def get_membership_for_user(self, user) -> Optional[UploaderIdentityMember]:
        if not hasattr(self, "__membership_cache"):
            self.__membership_cache = {}
        if user.pk not in self.__membership_cache:
            self.__membership_cache[user.pk] = self.members.filter(user=user).first()
        return self.__membership_cache[user.pk]

    def ensure_can_create_service_account(self, user: Optional[UserType]) -> None:
        if not user or not user.is_authenticated:
            raise ValidationError("Must be authenticated")
        membership = self.get_membership_for_user(user)
        if not membership:
            raise ValidationError("Must be a member to create a service account")
        if membership.role != UploaderIdentityMemberRole.owner:
            raise ValidationError("Must be an owner to create a service account")

    def ensure_can_edit_service_account(self, user: Optional[UserType]) -> None:
        if not user or not user.is_authenticated:
            raise ValidationError("Must be authenticated")
        membership = self.get_membership_for_user(user)
        if not membership:
            raise ValidationError("Must be a member to edit a service account")
        if membership.role != UploaderIdentityMemberRole.owner:
            raise ValidationError("Must be an owner to edit a service account")

    def ensure_can_delete_service_account(self, user: Optional[UserType]) -> None:
        if not user or not user.is_authenticated:
            raise ValidationError("Must be authenticated")
        membership = self.get_membership_for_user(user)
        if not membership:
            raise ValidationError("Must be a member to delete a service account")
        if membership.role != UploaderIdentityMemberRole.owner:
            raise ValidationError("Must be an owner to delete a service account")

    def ensure_can_generate_service_account_token(
        self, user: Optional[UserType]
    ) -> None:
        if not user or not user.is_authenticated:
            raise ValidationError("Must be authenticated")
        membership = self.get_membership_for_user(user)
        if not membership:
            raise ValidationError(
                "Must be a member to generate a service account token",
            )
        if membership.role != UploaderIdentityMemberRole.owner:
            raise ValidationError(
                "Must be an owner to generate a service account token",
            )

    def ensure_user_can_manage_members(self, user: Optional[UserType]) -> None:
        if not user or not user.is_authenticated:
            raise ValidationError("Must be authenticated")
        membership = self.get_membership_for_user(user)
        if not membership or membership.role != UploaderIdentityMemberRole.owner:
            raise ValidationError("Must be an owner to manage team members")

    def ensure_user_can_access(self, user: Optional[UserType]) -> None:
        if not user or not user.is_authenticated:
            raise ValidationError("Must be authenticated")
        if not self.get_membership_for_user(user):
            raise ValidationError("Must be a member to access team")

    def ensure_can_upload_package(self, user: Optional[UserType]) -> None:
        if not user or not user.is_authenticated:
            raise ValidationError("Must be authenticated")
        if not user.is_active:
            raise ValidationError("User has been deactivated")
        membership = self.get_membership_for_user(user)
        if not membership:
            raise ValidationError("Must be a member of identity to upload package")
        if not self.is_active:
            raise ValidationError(
                "The team has been deactivated and as such cannot receive new packages"
            )

    def can_user_upload(self, user: Optional[UserType]) -> bool:
        return check_validity(lambda: self.ensure_can_upload_package(user))

    def can_user_manage_members(self, user: Optional[UserType]) -> bool:
        return check_validity(lambda: self.ensure_user_can_manage_members(user))

    def can_user_create_service_accounts(self, user: Optional[UserType]) -> bool:
        return check_validity(lambda: self.ensure_can_create_service_account(user))

    def can_user_delete_service_accounts(self, user: Optional[UserType]) -> bool:
        return check_validity(lambda: self.ensure_can_delete_service_account(user))

    def can_user_access(self, user: Optional[UserType]) -> bool:
        return check_validity(lambda: self.ensure_user_can_access(user))
