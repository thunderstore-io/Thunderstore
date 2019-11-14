import uuid
import jwt
from django.core.exceptions import ValidationError

from django.db import models
from django.conf import settings

from core.utils import ChoiceEnum


class SecretTypeChoices(ChoiceEnum):
    HS256 = "HS256"
    RS256 = "RS256"


class IncomingJWTAuthConfiguration(models.Model):
    name = models.CharField(
        max_length=128,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    secret = models.TextField()
    secret_type = models.CharField(
        choices=SecretTypeChoices.as_choices(),
        max_length=16,
    )
    key_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

    class Meta:
        verbose_name = "Incoming JWT Auth Configuration"
        verbose_name_plural = "Incoming JWT Auth Configurations"

    def __str__(self) -> str:
        return f"{self.name}"

    def decode(self, data):
        if self.secret_type not in SecretTypeChoices.options():
            raise ValidationError("Invalid secret type in database, this could be a security issue!")
        return jwt.decode(data, self.secret, algorithms=[self.secret_type])

    @classmethod
    def decode_incoming_data(cls, data, key_id):
        configuration = cls.objects.get(key_id=key_id)
        result = configuration.decode(data)
        return {
            "user": configuration.user,
            "data": result,
        }
