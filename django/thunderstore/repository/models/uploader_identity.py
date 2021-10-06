from typing import Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Manager, Q, QuerySet
from django.urls import reverse

from thunderstore.core.types import UserType
from thunderstore.core.utils import ChoiceEnum, capture_exception, check_validity
from thunderstore.repository.models import Package
from thunderstore.repository.validators import PackageReferenceComponentValidator


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

    def owners(self) -> "QuerySet[UploaderIdentityMember]":  # TODO: Generic type
        return self.exclude(~Q(role=UploaderIdentityMemberRole.owner))

    def real_user_owners(
        self,
    ) -> "QuerySet[UploaderIdentityMember]":  # TODO: Generic type
        return self.real_users().exclude(~Q(role=UploaderIdentityMemberRole.owner))


class UploaderIdentityMember(models.Model):
    objects: "UploaderIdentityMemberManager[UploaderIdentityMember]" = (
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
        constraints = [
            models.UniqueConstraint(
                fields=("user", "identity"), name="one_membership_per_user"
            ),
        ]
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


def strip_unsupported_characters(val: str) -> str:
    whitelist = "abcdefghijklmnopqrstuvwxyz" "ABCDEFGHIJKLMNOPQRSTUVWXYZ" "0123456789_"
    result = "".join([x for x in val if x in whitelist])
    while result.startswith("_"):
        result = result[1:]
    while result.endswith("_"):
        result = result[:-1]
    return result


class UploaderIdentity(models.Model):
    objects: "Manager[UploaderIdentity]"
    members: "UploaderIdentityMemberManager[UploaderIdentityMember]"
    owned_packages: "Manager[Package]"

    name = models.CharField(
        max_length=64,
        unique=True,
        validators=[PackageReferenceComponentValidator("Author name")],
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Uploader Identity"
        verbose_name_plural = "Uploader Identities"

    def __str__(self):
        return self.name

    def validate(self):
        if self.pk:
            if not UploaderIdentity.objects.get(pk=self.pk).name == self.name:
                raise ValidationError("UploaderIdentity name is read only")
        else:
            for validator in self._meta.get_field("name").validators:
                validator(self.name)
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

    @property
    def service_accounts_url(self):
        return reverse(
            "settings.teams.detail.service_accounts",
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
    def get_or_create_for_user(cls, user: UserType) -> "Optional[UploaderIdentity]":
        name = strip_unsupported_characters(user.username)
        if not name:
            return None

        existing = cls.objects.filter(name__iexact=name).first()
        if existing:
            if existing.can_user_access(user):
                return existing
            else:
                return None
        else:
            identity = cls.objects.create(name=name)
            identity.add_member(user=user, role=UploaderIdentityMemberRole.owner)
            return identity

    @classmethod
    def get_default_for_user(
        cls, user: Optional[UserType]
    ) -> "Optional[UploaderIdentity]":
        if not user or not user.is_authenticated:
            return None

        default = cls.objects.filter(members__user=user).first()
        if default and default.can_user_access(user):
            return default

        try:
            return cls.get_or_create_for_user(user)
        except Exception as e:  # pragma: no cover
            capture_exception(e)
            return None

    def is_last_owner(self, member: Optional[UploaderIdentityMember]) -> bool:
        if not member:
            return False
        owners = self.members.real_user_owners()
        return member in owners and owners.count() <= 1

    def get_membership_for_user(self, user) -> Optional[UploaderIdentityMember]:
        if not hasattr(self, "__membership_cache"):
            self.__membership_cache = {}
        if user.pk not in self.__membership_cache:
            self.__membership_cache[user.pk] = self.members.filter(user=user).first()
        return self.__membership_cache[user.pk]

    def ensure_can_create_service_account(self, user: Optional[UserType]) -> None:
        if not user or not user.is_authenticated:
            raise ValidationError("Must be authenticated")
        if not user.is_active:
            raise ValidationError("User has been deactivated")
        membership = self.get_membership_for_user(user)
        if not membership:
            raise ValidationError("Must be a member to create a service account")
        if membership.role != UploaderIdentityMemberRole.owner:
            raise ValidationError("Must be an owner to create a service account")

    def ensure_can_edit_service_account(self, user: Optional[UserType]) -> None:
        if not user or not user.is_authenticated:
            raise ValidationError("Must be authenticated")
        if not user.is_active:
            raise ValidationError("User has been deactivated")
        membership = self.get_membership_for_user(user)
        if not membership:
            raise ValidationError("Must be a member to edit a service account")
        if membership.role != UploaderIdentityMemberRole.owner:
            raise ValidationError("Must be an owner to edit a service account")

    def ensure_can_delete_service_account(self, user: Optional[UserType]) -> None:
        if not user or not user.is_authenticated:
            raise ValidationError("Must be authenticated")
        if not user.is_active:
            raise ValidationError("User has been deactivated")
        membership = self.get_membership_for_user(user)
        if not membership:
            raise ValidationError("Must be a member to delete a service account")
        if membership.role != UploaderIdentityMemberRole.owner:
            raise ValidationError("Must be an owner to delete a service account")

    def ensure_user_can_manage_members(self, user: Optional[UserType]) -> None:
        if not user or not user.is_authenticated:
            raise ValidationError("Must be authenticated")
        if not user.is_active:
            raise ValidationError("User has been deactivated")
        if hasattr(user, "service_account"):
            raise ValidationError("Service accounts are unable to manage members")
        membership = self.get_membership_for_user(user)
        if not membership or membership.role != UploaderIdentityMemberRole.owner:
            raise ValidationError("Must be an owner to manage team members")

    def ensure_user_can_access(self, user: Optional[UserType]) -> None:
        if not user or not user.is_authenticated:
            raise ValidationError("Must be authenticated")
        if not user.is_active:
            raise ValidationError("User has been deactivated")
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

    def ensure_member_can_be_removed(
        self, member: Optional[UploaderIdentityMember]
    ) -> None:
        if not member:
            raise ValidationError("Invalid member")
        if member.identity != self:
            raise ValidationError("Member is not a part of this uploader identity")
        if self.is_last_owner(member):
            raise ValidationError("Cannot remove last owner from team")

    def ensure_member_role_can_be_changed(
        self, member: Optional[UploaderIdentityMember], new_role: Optional[str]
    ) -> None:
        if not member:
            raise ValidationError("Invalid member")
        if member.identity != self:
            raise ValidationError("Member is not a part of this uploader identity")
        if not new_role or new_role not in UploaderIdentityMemberRole.options():
            raise ValidationError("New role is invalid")
        if new_role != UploaderIdentityMemberRole.owner:
            if self.is_last_owner(member):
                raise ValidationError("Cannot remove last owner from team")

    def ensure_user_can_disband(self, user: Optional[UserType]):
        if not user or not user.is_authenticated:
            raise ValidationError("Must be authenticated")
        if not user.is_active:
            raise ValidationError("User has been deactivated")
        if hasattr(user, "service_account"):
            raise ValidationError("Service accounts are unable to disband teams")
        membership = self.get_membership_for_user(user)
        if not membership or membership.role != UploaderIdentityMemberRole.owner:
            raise ValidationError("Must be an owner to disband team")
        if self.owned_packages.exists():
            raise ValidationError("Unable to disband teams with packages")

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

    def can_member_be_removed(self, member: Optional[UploaderIdentityMember]) -> bool:
        return check_validity(lambda: self.ensure_member_can_be_removed(member))

    def can_member_role_be_changed(
        self, member: Optional[UploaderIdentityMember], new_role: Optional[str]
    ) -> bool:
        return check_validity(
            lambda: self.ensure_member_role_can_be_changed(member, new_role)
        )

    def can_user_disband(self, user: Optional[UserType]) -> bool:
        return check_validity(lambda: self.ensure_user_can_disband(user))
