from django.db.models import Count, Sum
from django.http import HttpRequest, HttpResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.api.serializers import CyberstormCommunitySerializer
from thunderstore.community.models import Community


class CommunityAPIView(APIView):
    permission_classes = []

    @swagger_auto_schema(
        responses={200: CyberstormCommunitySerializer()},
        operation_id="api.community",
    )
    def get(self, request: HttpRequest, community_identifier: str) -> HttpResponse:
        # TODO: Filter out the common shared packages somehow
        c = Community.objects.annotate(
            pkgs=Count("package_listings", distinct=True),
            downloads=Sum(
                "package_listings__package__versions__downloads", distinct=True
            ),
        ).get(
            identifier=community_identifier,
        )
        community = {
            "name": c.name,
            "namespace": c.identifier,
            "downloadCount": c.downloads,
            "packageCount": c.pkgs,
            "imageSource": c.icon.url if bool(c.icon) else None,
            "serverCount": 0,
            "description": c.description,
            "discordLink": c.discord_url,
        }

        return Response(community, status=status.HTTP_200_OK)


class CommunitiesAPIView(APIView):
    permission_classes = []

    @swagger_auto_schema(
        responses={200: CyberstormCommunitySerializer(many=True)},
        operation_id="api.communities",
    )
    def get(self, request: HttpRequest) -> HttpResponse:
        # TODO: Filter out the common shared packages somehow
        c_q = Community.objects.filter(is_listed=True,).annotate(
            pkgs=Count("package_listings", distinct=True),
            downloads=Sum(
                "package_listings__package__versions__downloads", distinct=True
            ),
        )
        communities = [
            {
                "name": c.name,
                "namespace": c.identifier,
                "downloadCount": c.downloads,
                "packageCount": c.pkgs,
                "imageSource": c.icon.url if bool(c.icon) else None,
                "serverCount": 0,
                "description": c.description,
                "discordLink": c.discord_url,
            }
            for c in c_q
        ]

        return Response(communities, status=status.HTTP_200_OK)
