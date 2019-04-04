from rest_framework.serializers import SerializerMethodField, ModelSerializer

from repository.models import Package, PackageVersion


class PackageVersionSerializer(ModelSerializer):
    download_url = SerializerMethodField()
    full_name = SerializerMethodField()

    def get_download_url(self, instance):
        url = instance.download_url
        if "request" in self.context:
            url = self.context["request"].build_absolute_uri(instance.download_url)
        return url

    def get_full_name(self, instance):
        return instance.full_version_name

    class Meta:
        model = PackageVersion
        exclude = ("file", "package", "id")


class PackageSerializer(ModelSerializer):
    versions = SerializerMethodField()
    owner = SerializerMethodField()
    maintainers = SerializerMethodField()
    full_name = SerializerMethodField()

    def get_versions(self, instance):
        versions = instance.available_versions
        return PackageVersionSerializer(versions, many=True, context=self._context).data

    def get_owner(self, instance):
        return instance.owner.username

    def get_maintainers(self, instance):
        return [
            maintainer.username for maintainer in instance.maintainers.all()
        ]

    def get_full_name(self, instance):
        return instance.full_package_name

    class Meta:
        model = Package
        exclude = ("id",)
        depth = 0
