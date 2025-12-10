from django.db.models import Exists, OuterRef, QuerySet
from rest_framework import serializers
from rest_framework.generics import ListAPIView, get_object_or_404

from thunderstore.api.cyberstorm.serializers import (
    CyberstormPackageDependencySerializer,
)
from thunderstore.api.cyberstorm.views.markdown import get_package_version
from thunderstore.api.pagination import PackageDependenciesPaginator
from thunderstore.api.utils import CyberstormAutoSchemaMixin, CyberstormTimedCacheMixin
from thunderstore.repository.models import Package, PackageVersion


class CyberstormPackageVersionSerializer(serializers.Serializer):
    version_number = serializers.CharField()
    datetime_created = serializers.DateTimeField(source="date_created")
    download_count = serializers.IntegerField(min_value=0, source="downloads")
    download_url = serializers.CharField(source="full_download_url")
    install_url = serializers.CharField()


class PackageVersionListAPIView(CyberstormTimedCacheMixin, CyberstormAutoSchemaMixin, ListAPIView):
    """
    Return a list of available versions of the package.
    """

    serializer_class = CyberstormPackageVersionSerializer
    # Cache for a month
    cache_max_age_in_seconds = 60 * 60 * 24 * 30

    def get_queryset(self):
        package = get_object_or_404(
            Package.objects.active(),
            namespace__name=self.kwargs["namespace_id"],
            name=self.kwargs["package_name"],
        )
        return package.versions.active()


class PackageVersionDependenciesListAPIView(CyberstormAutoSchemaMixin, ListAPIView):
    serializer_class = CyberstormPackageDependencySerializer
    pagination_class = PackageDependenciesPaginator

    def get_queryset(self) -> QuerySet[PackageVersion]:
        package_version = get_package_version(
            namespace_id=self.kwargs["namespace_id"],
            package_name=self.kwargs["package_name"],
            version_number=self.kwargs["version_number"],
        )

        qs = (
            package_version.dependencies.all()
            .select_related("package", "package__namespace")
            .annotate(
                package_has_active_versions=Exists(
                    PackageVersion.objects.filter(
                        package_id=OuterRef("package__pk"), is_active=True
                    )
                )
            )
            .order_by("package__namespace__name", "package__name")
        )

        return qs
