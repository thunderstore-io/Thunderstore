from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import ValidationError
from rest_framework.generics import RetrieveAPIView, get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from thunderstore.cache.cache import ManualCacheCommunityMixin
from thunderstore.cache.enums import CacheBustCondition
from thunderstore.repository.api.experimental.serializers import (
    MarkdownResponseSerializer,
    PackageVersionSerializerExperimental,
)
from thunderstore.repository.models import PackageVersion
from thunderstore.repository.package_reference import PackageReference


class PackageVersionDetailMixin(ManualCacheCommunityMixin, RetrieveAPIView):
    cache_until = CacheBustCondition.any_package_updated

    @swagger_auto_schema(tags=["experimental"])
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)

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


class PackageVersionDetailApiView(PackageVersionDetailMixin):
    """
    Get a single package version
    """

    permission_classes = [AllowAny]
    serializer_class = PackageVersionSerializerExperimental

    @swagger_auto_schema(
        operation_id="experimental_package_version_read",
        tags=["experimental"],
    )
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)


class PackageVersionChangelogApiView(PackageVersionDetailMixin):
    """
    Get a package verion's changelog
    """

    permission_classes = [AllowAny]
    serializer_class = MarkdownResponseSerializer

    @swagger_auto_schema(
        operation_id="experimental_package_version_changelog_read",
        tags=["experimental"],
    )
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer({"markdown": instance.changelog})
        return Response(serializer.data)


class PackageVersionReadmeApiView(PackageVersionDetailMixin):
    """
    Get a package verion's readme
    """

    permission_classes = [AllowAny]
    serializer_class = MarkdownResponseSerializer

    @swagger_auto_schema(
        operation_id="experimental_package_version_readme_read",
        tags=["experimental"],
    )
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer({"markdown": instance.readme})
        return Response(serializer.data)
