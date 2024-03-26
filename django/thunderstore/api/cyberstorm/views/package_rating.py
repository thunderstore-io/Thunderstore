from django.http import HttpRequest
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.api.utils import conditional_swagger_auto_schema
from thunderstore.repository.forms import RateForm
from thunderstore.repository.models import Package


class CyberstormPackageRatingRateRequestSerialiazer(serializers.Serializer):
    target_state = serializers.CharField()


class CyberstormPackageRatingRateResponseSerialiazer(serializers.Serializer):
    state = serializers.CharField()
    score = serializers.IntegerField()


class PackageRatingRateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @conditional_swagger_auto_schema(
        request_body=CyberstormPackageRatingRateRequestSerialiazer,
        responses={200: CyberstormPackageRatingRateResponseSerialiazer},
        operation_id="cyberstorm.package_rating.rate",
        tags=["cyberstorm"],
    )
    def post(self, request: HttpRequest, namespace_id: str, package_name: str):
        serializer = CyberstormPackageRatingRateRequestSerialiazer(data=request.data)
        serializer.is_valid(raise_exception=True)
        package = get_object_or_404(
            Package,
            namespace__name=namespace_id,
            name__iexact=package_name,
        )
        form = RateForm(
            user=request.user,
            package=package,
            data=serializer.validated_data,
        )
        if form.is_valid():
            (result_state, score) = form.execute()
            return Response(
                CyberstormPackageRatingRateResponseSerialiazer(
                    {"state": result_state, "score": score}
                ).data
            )
        else:
            raise ValidationError(form.errors)
