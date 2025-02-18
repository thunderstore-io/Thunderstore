from rest_framework import serializers
from rest_framework.generics import ListAPIView, get_object_or_404

from thunderstore.api.utils import CyberstormAutoSchemaMixin
from thunderstore.repository.models import Package


class CyberstormPackageVersionSerializer(serializers.Serializer):
    version_number = serializers.CharField()
    datetime_created = serializers.DateTimeField(source="date_created")
    download_count = serializers.IntegerField(min_value=0, source="downloads")
    download_url = serializers.CharField(source="full_download_url")
    install_url = serializers.CharField()


class PackageVersionListAPIView(CyberstormAutoSchemaMixin, ListAPIView):
    """
    Return a list of available versions of the package.
    """

    serializer_class = CyberstormPackageVersionSerializer

    def get_queryset(self):
        package = get_object_or_404(
            Package.objects.active(),
            namespace__name=self.kwargs["namespace_id"],
            name=self.kwargs["package_name"],
        )

        return package.versions.active()
