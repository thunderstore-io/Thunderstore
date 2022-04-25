from django.db.models import BigIntegerField, Count, QuerySet, Sum
from django.http import HttpRequest, HttpResponse
from drf_yasg.utils import swagger_auto_schema
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

    permission_classes = []

    @swagger_auto_schema(
        responses={200: FrontPageContentSerializer()},
        operation_id="experimental.frontend.frontpage",
    )
    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        queryset = self.get_queryset()
        serializer = self.serialize_results(queryset)

        return Response(serializer.data)

    def get_queryset(self) -> QuerySet[Community]:
        return (
            Community.objects.listed()
            .prefetch_related(
                "sites",
            )
            .annotate(
                package_downloads_total=Sum(
                    "package_listings__package__versions__downloads",
                    output_field=BigIntegerField(),
                ),
                package_count=Count("package_listings"),
            )
            .order_by("-package_count")
        )

    def serialize_results(
        self, queryset: QuerySet[Community]
    ) -> FrontPageContentSerializer:
        communities = [
            {
                "bg_image_src": c.site_image_url,
                "download_count": c.package_downloads_total or 0,
                "identifier": c.identifier,
                "name": c.name,
                "package_count": c.package_count,
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
