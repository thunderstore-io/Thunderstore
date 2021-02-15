from django.db import models
from django.shortcuts import redirect


class TimestampMixin(models.Model):
    datetime_created = models.DateTimeField(auto_now_add=True)
    datetime_updated = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        update_fields = kwargs.pop("update_fields", [])
        if update_fields:
            kwargs["update_fields"] = tuple(
                set(list(update_fields) + ["datetime_updated"])
            )
        super().save(*args, **kwargs)

    class Meta:
        abstract = True


class RequireAuthenticationMixin:
    def dispatch(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return redirect("index")
        return super().dispatch(*args, **kwargs)
