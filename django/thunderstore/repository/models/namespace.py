from __future__ import annotations

from typing import Optional

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Manager

import thunderstore.repository.models
from thunderstore.core.types import UserType
from thunderstore.repository.models.team import Team
from thunderstore.repository.validators import PackageReferenceComponentValidator


class Namespace(models.Model):
    objects: "Manager[Namespace]"
    owned_packages: "Manager[Package]"
    teams: "Manager[Team]"

    name = models.CharField(
        max_length=64,
        unique=True,
        validators=[PackageReferenceComponentValidator("Namespace name")],
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Namespace"
        verbose_name_plural = "Namespaces"

    def __str__(self):
        return self.name

    # def ensure_can_upload_package_with_team(team: Team, user: Optional[UserType]) -> bool:
    #     try:
    #         team.ensure_can_upload_package(user, namespace)
    #     except ValidationError:
    #         return False
    #     return True

    # def ensure_can_upload_package(self, user: Optional[UserType]) -> None:
    #     return any([Namespace.ensure_can_upload_package_with_team(team, user) for team in self.teams.all()])

    def can_user_access_with_team(team: Team, user: Optional[UserType]) -> bool:
        try:
            team.can_user_access(user)
        except ValidationError:
            return False
        return True

    def can_user_access(self, user: Optional[UserType]) -> None:
        return any(
            [
                Namespace.can_user_access_with_team(team, user)
                for team in self.teams.filter(members__user=user)
            ]
        )

    def can_user_upload_with_team(team: Team, user: Optional[UserType]) -> bool:
        try:
            team.can_user_upload(user)
        except ValidationError:
            return False
        return True

    def can_user_upload(self, user: Optional[UserType]) -> None:
        return any(
            [
                Namespace.can_user_upload_with_team(team, user)
                for team in self.teams.filter(members__user=user)
            ]
        )

    def validate(self):
        if self.pk:
            if not Namespace.objects.get(pk=self.pk).name == self.name:
                raise ValidationError("Namespace name is read only")
        else:
            for validator in self._meta.get_field("name").validators:
                validator(self.name)
            if Namespace.objects.filter(name__iexact=self.name.lower()).exists():
                raise ValidationError("The namespace name already exists")

    def save(self, *args, **kwargs):
        self.validate()
        return super().save(*args, **kwargs)
