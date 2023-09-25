from typing import Optional

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Manager

from django_extrafields.models import SafeOneToOneOrField

User = get_user_model()


class UserSettings(models.Model):
    objects: Manager["UserSettings"]

    user = SafeOneToOneOrField(
        User,
        related_name="settings",
        on_delete=models.CASCADE,
    )

    @classmethod
    def get_for_user(cls, user: User) -> Optional["UserSettings"]:
        settings = cls.objects.filter(user=user).first()
        return settings if settings else cls.objects.create(user=user)

    class Meta:
        verbose_name = "user settings"
        verbose_name_plural = "user settings"
