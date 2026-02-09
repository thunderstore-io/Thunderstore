from rest_framework import serializers

from thunderstore.api.cyberstorm.serializers.package import (
    CyberstormPackageTeamSerializer,
)
from thunderstore.api.cyberstorm.serializers.utils import EmptyStringAsNoneField


class PackageVersionResponseSerializer(serializers.Serializer):
    """
    Data shown on package version detail view.

    Expects an annotated and customized CustomListing object.
    """

    datetime_created = serializers.DateTimeField(source="date_created")
    dependency_count = serializers.IntegerField(min_value=0)
    description = serializers.CharField()
    download_count = serializers.IntegerField(source="downloads", min_value=0)
    download_url = serializers.CharField(source="full_download_url")
    full_version_name = serializers.CharField()
    icon_url = serializers.CharField(source="icon.url")
    install_url = serializers.CharField()
    name = serializers.CharField()
    version_number = serializers.CharField()
    namespace = serializers.CharField(source="package.namespace.name")
    size = serializers.IntegerField(min_value=0, source="file_size")
    team = CyberstormPackageTeamSerializer(source="owner")
    website_url = EmptyStringAsNoneField()
