from django.conf import settings
from django.db import models


class UserMeta(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    can_moderate_any_community = models.BooleanField(default=False)
