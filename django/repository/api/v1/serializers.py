from rest_framework.serializers import SerializerMethodField, ModelSerializer

from repository.models import Package, PackageVersion


class PackageVersionSerializer(ModelSerializer):
    download_url = SerializerMethodField()
    full_name = SerializerMethodField()
    dependencies = SerializerMethodField()

    def get_download_url(self, instance):
        url = instance.download_url
        if "request" in self.context:
            url = self.context["request"].build_absolute_uri(instance.download_url)
        return url

    def get_full_name(self, instance):
        return instance.full_version_name

    def get_dependencies(self, instance):
        return [
            dependency.full_version_name for dependency in instance.dependencies.all()
        ]

    class Meta:
        model = PackageVersion
        fields = (
            "name",
            "full_name",
            "description",
            "icon",
            "version_number",
            "dependencies",
            "download_url",
            "downloads",
            "date_created",
            "website_url",
            "is_active",
            "uuid4",
        )


class PackageSerializer(ModelSerializer):
    versions = SerializerMethodField()
    owner = SerializerMethodField()
    full_name = SerializerMethodField()
    package_url = SerializerMethodField()

    def get_versions(self, instance):
        versions = instance.available_versions
        return PackageVersionSerializer(versions, many=True, context=self._context).data

    def get_owner(self, instance):
        return instance.owner.name

    def get_full_name(self, instance):
        return instance.full_package_name

    def get_package_url(self, instance):
        return instance.full_url

    class Meta:
        model = Package
        fields = (
            "name",
            "full_name",
            "owner",
            "package_url",
            "date_created",
            "date_updated",
            "uuid4",
            "is_pinned",
            "versions",
        )
        depth = 0
