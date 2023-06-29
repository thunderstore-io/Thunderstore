from django.http import HttpRequest, HttpResponse
from rest_framework import permissions, status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.api.cyberstorm.serializers import LikePackageSerializerCyberstorm
from thunderstore.repository.models import Package, PackageRating
from thunderstore.repository.permissions import ensure_can_rate_package


class LikePackageAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request: HttpRequest, uuid4: str) -> HttpResponse:
        package = get_object_or_404(Package.objects.active(), uuid4=uuid4)
        user = request.user
        ensure_can_rate_package(user, package)
        target_state = request.data.get("target_state")
        if target_state == "rated":
            PackageRating.objects.get_or_create(rater=user, package=package)
            result_state = "rated"
        else:
            PackageRating.objects.filter(rater=user, package=package).delete()
            result_state = "unrated"
        return Response(
            LikePackageSerializerCyberstorm(
                {
                    "state": result_state,
                    "score": package.rating_score,
                }
            ).data,
            status=status.HTTP_200_OK,
        )
