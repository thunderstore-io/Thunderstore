from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import ValidationError
from rest_framework.generics import RetrieveAPIView, get_object_or_404

from thunderstore.cache.cache import CacheBustCondition, ManualCacheMixin
from thunderstore.repository.api.experimental.serializers import (
    PackageVersionSerializerExperimental,
)
from thunderstore.repository.models import PackageVersion
from thunderstore.repository.package_reference import PackageReference


class PackageVersionDetailApiView(ManualCacheMixin, RetrieveAPIView):
    """
    Get a single package version
    """

    cache_until = CacheBustCondition.any_package_updated
    serializer_class = PackageVersionSerializerExperimental

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        try:
            reference = PackageReference(
                namespace=self.kwargs["namespace"],
                name=self.kwargs["name"],
                version=self.kwargs["version"],
            )
        except ValueError as e:
            raise ValidationError(str(e))
        obj = get_object_or_404(queryset, **reference.get_filter_kwargs())
        self.check_object_permissions(self.request, obj)
        return obj

    def get_queryset(self):
        return (
            PackageVersion.objects.active()
            .select_related(
                "package",
                "package__owner",
            )
            .prefetch_related(
                "dependencies",
                "dependencies__package",
                "dependencies__package__owner",
            )
            .order_by(
                "-package__is_pinned",
                "package__is_deprecated",
                "-package__date_updated",
            )
        )

    @swagger_auto_schema(operation_id="experimental_package_version_read")
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)
