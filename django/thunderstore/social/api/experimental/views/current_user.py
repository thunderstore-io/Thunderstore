from typing import List, Optional, Set, TypedDict

from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.core.types import UserType


class CurrentUserExperimentalApiView(APIView):
    """
    Gets information about the current user, such as rated packages and permissions
    """

    def get(self, request, format=None):
        if request.user.is_authenticated:
            profile = get_user_profile(request.user)
        else:
            profile = get_empty_profile()

        return Response(profile)


class UserProfile(TypedDict):
    username: Optional[str]
    capabilities: Set[str]
    rated_packages: List[str]
    teams: List[str]


def get_empty_profile() -> UserProfile:
    return {
        "username": None,
        "capabilities": set(),
        "rated_packages": [],
        "teams": [],
    }


def get_user_profile(user: UserType) -> UserProfile:
    username = user.username
    capabilities = {"package.rate"}

    rated_packages = list(
        user.package_ratings.select_related("package").values_list(
            "package__uuid4",
            flat=True,
        ),
    )

    teams = list(
        user.teams.filter(team__is_active=True).values_list(
            "team__name",
            flat=True,
        ),
    )

    return {
        "username": username,
        "capabilities": capabilities,
        "rated_packages": rated_packages,
        "teams": teams,
    }
