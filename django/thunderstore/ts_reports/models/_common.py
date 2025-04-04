from django.db import models


class ActiveManager(models.Manager):
    def active(self):
        return self.exclude(is_active=False)
