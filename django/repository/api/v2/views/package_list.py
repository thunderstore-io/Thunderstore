from rest_framework.fields import SerializerMethodField
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.schemas import AutoSchema
from rest_framework.serializers import ModelSerializer

from core.cache import CacheBustCondition, cache_function_result, ManualCacheMixin
from repository.models import Package, PackageVersion


class PackagePaginator(PageNumberPagination):
    page_size = 30
    page_size_query_param = None


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
        ref_name = "PackageVersionV2"
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


class PackageSerializer(ModelSerializer):
    owner = SerializerMethodField()
    full_name = SerializerMethodField()
    package_url = SerializerMethodField()
    latest = PackageVersionSerializer()
    total_downloads = SerializerMethodField()

    def get_owner(self, instance):
        return instance.owner.name

    def get_full_name(self, instance):
        return instance.full_package_name

    def get_package_url(self, instance):
        return instance.full_url

    def get_total_downloads(self, instance):
        return instance.downloads

    class Meta:
        model = Package
        ref_name = "PackageV2"
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


@cache_function_result(cache_until=CacheBustCondition.any_package_updated)
def get_mod_list_queryset():
    return (
        Package.objects
        .active()
        .select_related(
            "owner",
            "latest",
        )
        .prefetch_related(
            "latest__dependencies",
        )
        .order_by("-is_pinned", "is_deprecated", "-date_updated")
    )


class PackageListSchema(AutoSchema):
    pass


class PackageListApiView(ManualCacheMixin, ListAPIView):
    """
    Lists all available packages
    """
    cache_until = CacheBustCondition.any_package_updated
    serializer_class = PackageSerializer
    pagination_class = PackagePaginator
    schema = PackageListSchema()

    def get_queryset(self):
        return get_mod_list_queryset()
