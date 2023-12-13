from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.community.models.community import Community
from thunderstore.frontend.api.experimental.serializers.views import (
    FrontPageContentSerializer,
)


class FrontPageApiView(APIView):
    """
    Return information required to render the site's front page.
    """

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        responses={200: FrontPageContentSerializer()},
        operation_id="experimental.frontend.frontpage",
        deprecated=True,
        tags=["experimental"],
    )
    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        queryset = self.get_queryset()
        serializer = self.serialize_results(queryset)

        return Response(serializer.data)

    def get_queryset(self) -> QuerySet[Community]:
        return (
            Community.objects.listed()
            .prefetch_related("sites")
            .order_by("-aggregated_fields__package_count")
        )

    def serialize_results(
        self,
        queryset: QuerySet[Community],
    ) -> FrontPageContentSerializer:
        communities = [
            {
                "bg_image_src": c.background_image_url,
                "cover_image_src": c.cover_image_url,
                "download_count": c.aggregated.download_count,
                "identifier": c.identifier,
                "name": c.name,
                "package_count": c.aggregated.package_count,
            }
            for c in queryset
        ]

        return FrontPageContentSerializer(
            {
                "communities": communities,
                "download_count": sum(c["download_count"] for c in communities),
                "package_count": sum(c["package_count"] for c in communities),
            },
        )
