import pickle
from datetime import timedelta

from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from thunderstore.core.mixins import TimestampMixin


class DatabaseCache(TimestampMixin, models.Model):
    key = models.CharField(max_length=512, unique=True, db_index=True)
    content = models.BinaryField(blank=True, null=True)
    expires_on = models.DateTimeField(blank=True, null=True)
    hits = models.PositiveIntegerField(default=0)

    @classmethod
    def get(cls, key, default=None):
        query = cls.objects.filter(key=key).exclude(
            Q(expires_on__lte=timezone.now()) & ~Q(expires_on=None)
        )
        result = query.values_list("content", flat=True)
        if result:
            query.update(hits=F("hits") + 1)
            return pickle.loads(result[0])
        return default

    @classmethod
    def set(cls, key, content, timeout=None):
        if timeout:
            expiry = timezone.now() + timedelta(seconds=timeout)
        else:
            expiry = None
        return cls.objects.update_or_create(
            key=key,
            defaults=dict(content=pickle.dumps(content), expires_on=expiry),
        )[0]
