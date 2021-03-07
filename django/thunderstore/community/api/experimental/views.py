from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.community.api.experimental.serializers import (
    CommunitySerializer,
    PackageCategorySerializer,
)
from thunderstore.community.models import Community


class CommunitiesExperimentalApiView(APIView):
    def get(self, request, format=None):
        communities = CommunitySerializer(Community.objects.listed(), many=True)
        return Response(
            {
                "communities": communities.data,
            },
        )


class PackageCategoriesExperimentalApiView(APIView):
    def get(self, request, format=None, **kwargs):
        community_identifier = kwargs["community"]
        community = Community.objects.filter(identifier=community_identifier).first()
        if not community:
            return Response({"error": "Community not found"}, 404)
        communities = PackageCategorySerializer(community.package_categories, many=True)
        return Response(
            {
                "packageCategories": communities.data,
            },
        )
