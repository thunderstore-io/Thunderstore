from rest_framework import serializers
from rest_framework.generics import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.api.cyberstorm.serializers import (
    CyberstormPackageCategorySerializer,
    CyberstormPackageListingSectionSerializer,
)
from thunderstore.api.utils import conditional_swagger_auto_schema
from thunderstore.community.models import Community


class CommunityFiltersAPIViewSerializer(serializers.Serializer):
    package_categories = CyberstormPackageCategorySerializer(many=True)
    sections = CyberstormPackageListingSectionSerializer(many=True)


class CommunityFiltersAPIView(APIView):
    """
    Return info about PackageCategories and PackageListingSections so
    they can be used as filters.
    """

    queryset = Community.objects.prefetch_related("package_categories")
    serializer_class = CommunityFiltersAPIViewSerializer

    @conditional_swagger_auto_schema(
        tags=["cyberstorm"],
        responses={200: serializer_class()},
    )
    def get(self, request: Request, community_id: str):
        community = get_object_or_404(self.queryset, identifier=community_id)
        filters = {
            "package_categories": community.package_categories.all(),
            "sections": community.package_listing_sections.listed().order_by(
                "priority",
            ),
        }

        return Response(self.serializer_class(filters).data)
