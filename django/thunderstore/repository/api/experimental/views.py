from django.db.models import Count, QuerySet, Sum
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView, get_object_or_404
from rest_framework.pagination import CursorPagination
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.core.cache import CacheBustCondition, ManualCacheMixin
from thunderstore.repository.api.experimental.serializers import (
    PackageSerializerExperimental,
    PackageUploadSerializerExperiemental,
    PackageVersionSerializerExperimental,
)
from thunderstore.repository.models import Package, PackageVersion
from thunderstore.repository.package_reference import PackageReference


def get_package_queryset() -> "QuerySet[Package]":
    return (
        Package.objects.active()
        .select_related(
            "owner",
            "latest",
            "latest__package",
            "latest__package__owner",
        )
        .prefetch_related(
            "latest__dependencies",
            "latest__dependencies__package",
            "latest__dependencies__package__owner",
            "community_listings",
            "community_listings__categories",
            "community_listings__community",
        )
        .annotate(
            _total_downloads=Sum("versions__downloads"),
            _rating_score=Count("package_ratings"),
        )
    )


class CustomCursorPagination(CursorPagination):
    ordering = "-date_created"
    page_size = 50


class PackageListApiView(ManualCacheMixin, ListAPIView):
    """
    Lists all available packages
    """

    cache_until = CacheBustCondition.any_package_updated
    serializer_class = PackageSerializerExperimental
    pagination_class = CustomCursorPagination

    def get_queryset(self):
        return get_package_queryset()


class PackageDetailApiView(ManualCacheMixin, RetrieveAPIView):
    """
    Get a single package
    """

    cache_until = CacheBustCondition.any_package_updated
    serializer_class = PackageSerializerExperimental

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        try:
            reference = PackageReference(
                namespace=self.kwargs["namespace"],
                name=self.kwargs["name"],
            )
        except ValueError as e:
            raise ValidationError(str(e))
        obj = get_object_or_404(queryset, **reference.get_filter_kwargs())
        self.check_object_permissions(self.request, obj)
        return obj

    def get_queryset(self):
        return get_package_queryset()

    @swagger_auto_schema(operation_id="experimental_package_read")
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)


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


class UploadPackageApiView(APIView):
    """
    Uploads a package. Requires multipart/form-data.
    """

    parser_classes = [MultiPartParser]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PackageUploadSerializerExperiemental(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        package_version = serializer.save()
        serializer = PackageVersionSerializerExperimental(
            instance=package_version,
            context={"request": request},
        )
        return Response(serializer.data)
