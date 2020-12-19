from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ModelSerializer

from thunderstore.community.models import PackageListing
from thunderstore.repository.models import Package, PackageVersion


class PackageVersionSerializerExperimental(ModelSerializer):
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
        ref_name = "PackageVersionExperimental"
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
        )


class PackageSerializerExperimental(ModelSerializer):
    owner = SerializerMethodField()
    full_name = SerializerMethodField()
    package_url = SerializerMethodField()
    latest = PackageVersionSerializerExperimental()
    total_downloads = SerializerMethodField()

    def get_owner(self, instance):
        return instance.owner.name

    def get_full_name(self, instance):
        return instance.full_package_name

    def get_package_url(self, instance):
        return instance.get_full_url(self.context["community_site"].site)

    def get_total_downloads(self, instance):
        return instance.downloads

    class Meta:
        model = Package
        ref_name = "PackageExperimental"
        fields = (
            "name",
            "full_name",
            "owner",
            "package_url",
            "date_created",
            "date_updated",
            "rating_score",
            "is_pinned",
            "is_deprecated",
            "total_downloads",
            "latest",
        )
        depth = 0


class PackageListingSerializerExperimental(ModelSerializer):
    package = PackageSerializerExperimental()
    categories = SerializerMethodField()

    def get_categories(self, instance):
        return set(instance.categories.all().values_list("name", flat=True))

    class Meta:
        model = PackageListing
        ref_name = "PackageListingExperimental"
        fields = (
            "package",
            "has_nsfw_content",
            "categories",
        )
