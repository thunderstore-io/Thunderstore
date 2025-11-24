from django.db.models import Count
from django.http import HttpRequest
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.api.cyberstorm.serializers.package_version import (
    PackageVersionResponseSerializer,
)
from thunderstore.api.utils import (
    CyberstormAutoSchemaMixin,
    conditional_swagger_auto_schema,
)
from thunderstore.repository.models.package_version import PackageVersion


class PackageVersionAPIView(CyberstormAutoSchemaMixin, APIView):
    @conditional_swagger_auto_schema(
        responses={200: PackageVersionResponseSerializer},
        operation_id="cyberstorm.package_version",
        tags=["cyberstorm"],
    )
    def get(
        self,
        request: HttpRequest,
        namespace_id: str,
        package_name: str,
        version_number: str,
    ) -> Response:
        instance = get_object_or_404(
            PackageVersion.objects.filter(is_active=True)
            .select_related(
                "package",
                "package__namespace",
            )
            .prefetch_related(
                "package__owner__members",
            )
            .annotate(
                dependency_count=Count(
                    "dependencies",
                )
            ),
            package__namespace__name=namespace_id,
            name=package_name,
            version_number=version_number,
        )

        response_serializer = PackageVersionResponseSerializer(instance=instance)
        response = Response(response_serializer.data, status=status.HTTP_200_OK)
        response["Cache-Control"] = "public, max-age=600"
        return response
