from rest_framework import serializers


class PackageDownloadMetricsSerializer(serializers.Serializer):
    """
    Historical download metrics for a package.
    """

    date = serializers.DateField(help_text="Date for this data point (YYYY-MM-DD)")
    count = serializers.IntegerField(
        min_value=0,
        help_text="Number of downloads recorded on this date",
    )


class PackageVersionDownloadMetricsResponseSerializer(serializers.Serializer):
    """
    Response containing historical download data for a package version.
    """

    namespace = serializers.CharField(
        help_text="Namespace (owner) of the package",
    )
    name = serializers.CharField(
        help_text="Name of the package",
    )
    version_number = serializers.CharField(
        help_text="Version number of the package",
    )
    total_downloads = serializers.IntegerField(
        min_value=0,
        help_text="Total all-time downloads for this specific version",
    )
    daily_downloads = PackageDownloadMetricsSerializer(
        many=True,
        help_text="Array of daily download counts for the requested time period",
    )


class PackageDownloadMetricsResponseSerializer(serializers.Serializer):
    """
    Response containing aggregated historical download data for all versions
    of a package.
    """

    namespace = serializers.CharField(
        help_text="Namespace (owner) of the package",
    )
    name = serializers.CharField(
        help_text="Name of the package",
    )
    total_downloads = serializers.IntegerField(
        min_value=0,
        help_text="Total all-time downloads across all versions of this package",
    )
    daily_downloads = PackageDownloadMetricsSerializer(
        many=True,
        help_text="Array of daily download counts aggregated across all versions",
    )

