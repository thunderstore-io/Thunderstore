from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.api.cyberstorm.services.package import rate_package
from thunderstore.api.utils import conditional_swagger_auto_schema
from thunderstore.repository.models import Package


class CyberstormRatePackageRequestSerializer(serializers.Serializer):
    target_state = serializers.CharField()


class CyberstormRatePackageResponseSerializer(serializers.Serializer):
    state = serializers.CharField()
    score = serializers.IntegerField()


class RatePackageAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_package(self, namespace_name: str, package_name: str) -> Package:
        package = get_object_or_404(
            Package.objects.active(),
            namespace__name=namespace_name,
            name=package_name,
        )
        return package

    @conditional_swagger_auto_schema(
        request_body=CyberstormRatePackageRequestSerializer,
        responses={200: CyberstormRatePackageResponseSerializer},
        operation_id="cyberstorm.package.rate",
        tags=["cyberstorm"],
    )
    def post(self, request: HttpRequest, namespace_id: str, package_name: str):
        serializer = CyberstormRatePackageRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_state = serializer.validated_data["target_state"]
        package = self.get_package(namespace_id, package_name)

        rating_score, result_state = rate_package(
            package=package,
            agent=request.user,
            target_state=target_state,
        )
        response_data = {"state": result_state, "score": rating_score}

        return Response(
            CyberstormRatePackageResponseSerializer(response_data).data,
            status=status.HTTP_200_OK,
        )
