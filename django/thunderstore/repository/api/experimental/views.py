import json

from django.db.models import Q
from django.http import HttpResponse
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.schemas import AutoSchema
from rest_framework.views import APIView

from thunderstore.community.models import CommunitySite, PackageListing
from thunderstore.core.cache import (
    BackgroundUpdatedCacheMixin,
    CacheBustCondition,
    cache_function_result,
)
from thunderstore.core.utils import CommunitySiteSerializerContext
from thunderstore.repository.api.experimental.serializers import (
    PackageListingSerializerExperimental,
    PackageUploadSerializer,
    PackageVersionSerializer,
)
from thunderstore.repository.models.package_version import PackageVersion


@cache_function_result(cache_until=CacheBustCondition.any_package_updated)
def get_mod_list_queryset(community_site: CommunitySite):
    return (
        PackageListing.objects.active()
        .exclude(~Q(community=community_site.community))
        .select_related(
            "package",
            "package__owner",
            "package__latest",
        )
        .prefetch_related(
            "package__latest__dependencies",
        )
        .order_by(
            "-package__is_pinned", "package__is_deprecated", "-package__date_updated"
        )
    )


class PackageListSchema(AutoSchema):
    pass


class PackageListApiView(
    BackgroundUpdatedCacheMixin, CommunitySiteSerializerContext, ListAPIView
):
    """
    Lists all available packages
    """

    cache_until = CacheBustCondition.any_package_updated
    serializer_class = PackageListingSerializerExperimental
    schema = PackageListSchema()

    @classmethod
    def get_no_cache_response(cls):
        return HttpResponse(
            json.dumps({"error": "No cache available"}),
            status=503,
            content_type="application/json",
        )

    def get_queryset(self):
        return get_mod_list_queryset(self.request.community_site)


class UploadPackageApiView(APIView):
    """
    Uploads a package. Requires multipart/form-data.
    """

    parser_classes = [MultiPartParser]

    def post(self, request):
        categories = request.data.get("categories")
        if categories:
            try:
                request.data["categories"] = json.loads(categories)
            except json.JSONDecodeError:
                return Response(
                    {"error": "Invalid"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        serializer = PackageUploadSerializer(
            data=request.data,
            context={"request": request},
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        package_version = serializer.save()
        serializer = PackageVersionSerializer(instance=package_version)
        return Response(serializer.data)
