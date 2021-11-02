from __future__ import annotations

from typing import Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Manager, Q, QuerySet
from django.urls import reverse

import thunderstore.repository.models
from thunderstore.core.types import UserType
from thunderstore.core.utils import ChoiceEnum, capture_exception, check_validity
from thunderstore.repository.validators import PackageReferenceComponentValidator


class TeamMemberRole(ChoiceEnum):
    owner = "owner"
    member = "member"


class TeamMemberManager(models.Manager):
    def real_users(self) -> "QuerySet[TeamMember]":  # TODO: Generic type
        return self.exclude(~Q(user__service_account=None))

    def service_accounts(
        self,
    ) -> "QuerySet[TeamMember]":  # TODO: Generic type
        return self.exclude(user__service_account=None)

    def owners(self) -> "QuerySet[TeamMember]":  # TODO: Generic type
        return self.exclude(~Q(role=TeamMemberRole.owner))

    def real_user_owners(
        self,
    ) -> "QuerySet[TeamMember]":  # TODO: Generic type
        return self.real_users().exclude(~Q(role=TeamMemberRole.owner))


class TeamMember(models.Model):
    objects: "TeamMemberManager[TeamMember]" = TeamMemberManager()

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="teams",
        on_delete=models.CASCADE,
    )
    team = models.ForeignKey(
        "repository.Team",
        related_name="members",
        on_delete=models.CASCADE,
    )
    role = models.CharField(
        max_length=64,
        default=TeamMemberRole.member,
        choices=TeamMemberRole.as_choices(),
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "team"), name="one_membership_per_user"
            ),
        ]
        verbose_name = "Team Member"
        verbose_name_plural = "Team Members"

    @property
    def can_be_demoted(self):
        return self.role == TeamMemberRole.owner

    @property
    def can_be_promoted(self):
        return self.role == TeamMemberRole.member

    def __str__(self):
        return f"{self.user.username} membership to {self.team.name}"


def strip_unsupported_characters(val: str) -> str:
    whitelist = "abcdefghijklmnopqrstuvwxyz" "ABCDEFGHIJKLMNOPQRSTUVWXYZ" "0123456789_"
    result = "".join([x for x in val if x in whitelist])
    while result.startswith("_"):
        result = result[1:]
    while result.endswith("_"):
        result = result[:-1]
    return result


class Team(models.Model):
    objects: "Manager[Team]"
    members: "TeamMemberManager[TeamMember]"

    name = models.CharField(
        max_length=64,
        unique=True,
        validators=[PackageReferenceComponentValidator("Author name")],
    )
    is_active = models.BooleanField(default=True)
    namespaces = models.ManyToManyField(
        "repository.Namespace",
        related_name="teams",
    )

    class Meta:
        verbose_name = "Team"
        verbose_name_plural = "Teams"

    def __str__(self):
        return self.name

    def validate(self):
        if self.pk:
            if not Team.objects.get(pk=self.pk).name == self.name:
                raise ValidationError("Team name is read only")
        else:
            for validator in self._meta.get_field("name").validators:
                validator(self.name)
            if Team.objects.filter(name__iexact=self.name.lower()).exists():
                raise ValidationError("The author name already exists")

    def save(self, *args, **kwargs):
        self.validate()
        return super().save(*args, **kwargs)

    @property
    def real_user_count(self):
        return self.members.real_users().count()

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

    def add_member(self, user: UserType, role: str) -> TeamMember:
        return TeamMember.objects.create(
            team=self,
            user=user,
            role=role,
        )

    @classmethod
    @transaction.atomic
    def get_or_create_for_user(cls, user: UserType) -> "Optional[Team]":
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
            team = cls.objects.create(name=name)
            team.add_member(user=user, role=TeamMemberRole.owner)
            return team

    @classmethod
    def get_default_for_user(cls, user: Optional[UserType]) -> "Optional[Team]":
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

    def is_last_owner(self, member: Optional[TeamMember]) -> bool:
        if not member:
            return False
        owners = self.members.real_user_owners()
        return member in owners and owners.count() <= 1

    def get_membership_for_user(self, user) -> Optional[TeamMember]:
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
        if membership.role != TeamMemberRole.owner:
            raise ValidationError("Must be an owner to create a service account")

    def ensure_can_edit_service_account(self, user: Optional[UserType]) -> None:
        if not user or not user.is_authenticated:
            raise ValidationError("Must be authenticated")
        if not user.is_active:
            raise ValidationError("User has been deactivated")
        membership = self.get_membership_for_user(user)
        if not membership:
            raise ValidationError("Must be a member to edit a service account")
        if membership.role != TeamMemberRole.owner:
            raise ValidationError("Must be an owner to edit a service account")

    def ensure_can_delete_service_account(self, user: Optional[UserType]) -> None:
        if not user or not user.is_authenticated:
            raise ValidationError("Must be authenticated")
        if not user.is_active:
            raise ValidationError("User has been deactivated")
        membership = self.get_membership_for_user(user)
        if not membership:
            raise ValidationError("Must be a member to delete a service account")
        if membership.role != TeamMemberRole.owner:
            raise ValidationError("Must be an owner to delete a service account")

    def ensure_user_can_manage_members(self, user: Optional[UserType]) -> None:
        if not user or not user.is_authenticated:
            raise ValidationError("Must be authenticated")
        if not user.is_active:
            raise ValidationError("User has been deactivated")
        if hasattr(user, "service_account"):
            raise ValidationError("Service accounts are unable to manage members")
        membership = self.get_membership_for_user(user)
        if not membership or membership.role != TeamMemberRole.owner:
            raise ValidationError("Must be an owner to manage team members")

    def ensure_user_can_access(self, user: Optional[UserType]) -> None:
        if not user or not user.is_authenticated:
            raise ValidationError("Must be authenticated")
        if not user.is_active:
            raise ValidationError("User has been deactivated")
        if not self.get_membership_for_user(user):
            raise ValidationError("Must be a member to access team")

    def ensure_can_upload_package(
        self,
        user: Optional[UserType],
        namespace: Optional[Namespace] = None,
        check_namespace: bool = True,
    ) -> None:
        if not user or not user.is_authenticated:
            raise ValidationError("Must be authenticated")
        if not user.is_active:
            raise ValidationError("User has been deactivated")
        membership = self.get_membership_for_user(user)
        if not membership:
            raise ValidationError("Must be a member of team to upload package")
        if not self.is_active:
            raise ValidationError(
                "The team has been deactivated and as such cannot receive new packages"
            )
        if (
            check_namespace
            and not namespace
            or check_namespace
            and not namespace in self.namespaces.all()
        ):
            raise ValidationError(
                "Team must be a owner of the namespace to upload package"
            )

    def ensure_member_can_be_removed(self, member: Optional[TeamMember]) -> None:
        if not member:
            raise ValidationError("Invalid member")
        if member.team != self:
            raise ValidationError("Member is not a part of this team")
        if self.is_last_owner(member):
            raise ValidationError("Cannot remove last owner from team")

    def ensure_member_role_can_be_changed(
        self, member: Optional[TeamMember], new_role: Optional[str]
    ) -> None:
        if not member:
            raise ValidationError("Invalid member")
        if member.team != self:
            raise ValidationError("Member is not a part of this team")
        if not new_role or new_role not in TeamMemberRole.options():
            raise ValidationError("New role is invalid")
        if new_role != TeamMemberRole.owner:
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
        if not membership or membership.role != TeamMemberRole.owner:
            raise ValidationError("Must be an owner to disband team")

    def can_user_upload(self, user: Optional[UserType]) -> bool:
        return check_validity(
            lambda: self.ensure_can_upload_package(user, check_namespace=False)
        )

    def can_user_manage_members(self, user: Optional[UserType]) -> bool:
        return check_validity(lambda: self.ensure_user_can_manage_members(user))

    def can_user_create_service_accounts(self, user: Optional[UserType]) -> bool:
        return check_validity(lambda: self.ensure_can_create_service_account(user))

    def can_user_delete_service_accounts(self, user: Optional[UserType]) -> bool:
        return check_validity(lambda: self.ensure_can_delete_service_account(user))

    def can_user_access(self, user: Optional[UserType]) -> bool:
        return check_validity(lambda: self.ensure_user_can_access(user))

    def can_member_be_removed(self, member: Optional[TeamMember]) -> bool:
        return check_validity(lambda: self.ensure_member_can_be_removed(member))

    def can_member_role_be_changed(
        self, member: Optional[TeamMember], new_role: Optional[str]
    ) -> bool:
        return check_validity(
            lambda: self.ensure_member_role_can_be_changed(member, new_role)
        )

    def can_user_disband(self, user: Optional[UserType]) -> bool:
        return check_validity(lambda: self.ensure_user_can_disband(user))
