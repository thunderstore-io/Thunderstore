from typing import Any

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, connections, models
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse

from thunderstore.cache.storage import CACHE_STORAGE
from thunderstore.core.utils import extend_update_fields_if_present


class TimestampMixin(models.Model):
    datetime_created = models.DateTimeField(auto_now_add=True)
    datetime_updated = models.DateTimeField(auto_now=True)

    def save(self, **kwargs):
        kwargs = extend_update_fields_if_present(kwargs, "datetime_updated")
        super().save(**kwargs)

    class Meta:
        abstract = True


class RequireAuthenticationMixin:
    def dispatch(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return redirect("index")
        return super().dispatch(*args, **kwargs)


def get_package_cache_filepath(_, filename: str) -> str:
    return f"cache/api/v1/package/{filename}"


class S3FileMixinQueryset(models.QuerySet):
    def active(self) -> models.QuerySet:
        return self.exclude(Q(is_deleted=True) | Q(data=None))

    def delete(self):
        # Disallow bulk-delete to ensure deletion happens properly.
        raise NotImplementedError(
            f"Delete is not supported for {self.__class__.__name__}"
        )


class SafeDeleteMixin(models.Model):
    is_deleted = models.BooleanField(default=False)

    def _delete_file(self, using: str = None):
        # We need to ensure any potential failure status is recorded to the database
        # appropriately. Easiest way to do this is just to ensure we're not in a
        # transaction, which could end up rolling back our failure status elsewhere
        # from the database. It is not the best solution, but works in preventing
        # accidental bugs due to mishandled transaction usage.
        if (
            connections[using or DEFAULT_DB_ALIAS].in_atomic_block
            and not settings.DISABLE_TRANSACTION_CHECKS
        ):
            raise RuntimeError("Must not be called during a transaction")

        # We use a separate is_deleted flag to ensure transactional safety. It
        # might be possible for a delete to succeed without it being recorded
        # to the database otherwise, as deletion normally happens before
        # a db write.
        self.is_deleted = True
        self.save(update_fields=("is_deleted",))
        self.on_safe_delete()

    def on_safe_delete(self):
        """
        Actual data deletion should be handled in this wrapper, which ensures
        the is_deleted flag has been set to True and committed to the databse
        before this is ever called.
        """
        pass

    def delete(self, using: str = None, **kwargs: Any):
        self._delete_file(using=using)
        super().delete(using=using, **kwargs)

    class Meta:
        abstract = True


class S3FileMixin(SafeDeleteMixin):
    objects: S3FileMixinQueryset["S3FileMixin"] = S3FileMixinQueryset.as_manager()

    data = models.FileField(
        upload_to=get_package_cache_filepath,
        storage=CACHE_STORAGE,
        blank=True,
        null=True,
    )
    content_type = models.TextField()
    content_encoding = models.TextField()
    last_modified = models.DateTimeField()

    def on_safe_delete(self):
        self.data.delete()

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["last_modified"]),
        ]


class AdminLinkMixin(models.Model):
    def get_admin_url(self):
        return reverse(
            f"admin:{self._meta.app_label}_{self._meta.model_name}_change",
            args=[self.pk],
        )

    class Meta:
        abstract = True


# AllowAllCORSMixin must be inherited before APIView / GenericAPIView
class AllowAllCORSMixin:
    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET"
        return response
