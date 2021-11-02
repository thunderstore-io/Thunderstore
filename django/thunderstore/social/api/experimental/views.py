from rest_framework.response import Response
from rest_framework.views import APIView


class CurrentUserExperimentalApiView(APIView):
    """
    Gets information about the current user, such as rated packages and permissions
    """

    def get(self, request, format=None):
        username = None
        capabilities = set()
        rated_packages = []
        teams = []
        if request.user.is_authenticated:
            username = request.user.username
            capabilities.add("package.rate")
            rated_packages = request.user.package_ratings.select_related(
                "package"
            ).values_list("package__uuid4", flat=True)
            teams = request.user.teams.values_list("team__name")
            teams = [team[0] for team in teams]
        return Response(
            {
                "username": username,
                "capabilities": capabilities,
                "ratedPackages": rated_packages,
                "teams": teams,
            },
        )
