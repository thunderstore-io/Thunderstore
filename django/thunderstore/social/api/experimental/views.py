from rest_framework.response import Response
from rest_framework.views import APIView


class CurrentUserExperimentalApiView(APIView):
    """
    Gets information about the current user, such as rated packages and permissions
    """

    def get(self, request, format=None):
        capabilities = set()
        rated_packages = []
        teams = []
        if request.user.is_authenticated:
            capabilities.add("package.rate")
            rated_packages = request.user.package_ratings.select_related(
                "package"
            ).values_list("package__uuid4", flat=True)
            teams = request.user.uploader_identities.values_list("identity__name")
        return Response(
            {
                "capabilities": capabilities,
                "ratedPackages": rated_packages,
                "teams": teams,
            },
        )
