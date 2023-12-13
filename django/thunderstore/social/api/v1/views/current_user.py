from drf_yasg.utils import swagger_auto_schema
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class CurrentUserInfoView(APIView):
    """
    Gets information about the current user, such as rated packages and permissions
    """

    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [AllowAny]

    @swagger_auto_schema(tags=["v1"])
    def get(self, request, format=None, community_identifier=None):
        capabilities = set()
        rated_packages = []
        if request.user.is_authenticated:
            capabilities.add("package.rate")
            rated_packages = request.user.package_ratings.select_related(
                "package"
            ).values_list("package__uuid4", flat=True)
        return Response({"capabilities": capabilities, "ratedPackages": rated_packages})
