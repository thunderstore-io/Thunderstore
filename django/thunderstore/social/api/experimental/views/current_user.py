import datetime
from typing import List, Optional, Set, TypedDict

from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.account.models.user_flag import UserFlag
from thunderstore.core.types import UserType


class CurrentUserExperimentalApiView(APIView):
    """
    Gets information about the current user, such as rated packages and permissions
    """

    @swagger_auto_schema(tags=["experimental"])
    def get(self, request, format=None):
        if request.user.is_authenticated:
            profile = get_user_profile(request.user)
        else:
            profile = get_empty_profile()

        return Response(profile)


class SubscriptionStatus(TypedDict):
    expires: Optional[datetime.datetime]


class SubscriptionStatusSerializer(serializers.Serializer):
    expires = serializers.DateField()


class UserProfile(TypedDict):
    username: Optional[str]
    capabilities: Set[str]
    subscription: SubscriptionStatus
    rated_packages: List[str]
    teams: List[str]


class UserProfileSerializer(serializers.Serializer):
    username = serializers.CharField()
    capabilities = serializers.ListField()
    subscription = SubscriptionStatusSerializer()
    rated_packages = serializers.ListField()
    teams = serializers.ListField()


def get_empty_profile() -> UserProfile:
    return {
        "username": None,
        "capabilities": set(),
        "subscription": get_subscription_status(user=None),
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
        "subscription": get_subscription_status(user),
        "rated_packages": rated_packages,
        "teams": teams,
    }


def get_subscription_status(user: Optional[UserType]) -> SubscriptionStatus:
    """
    Return information regarding user's paid subscription plan.

    TODO: This is just a stub. The real thing (as well as the definition
    for SubscriptionStatus) should be implemented in our proprietary
    django_paypal package or some other more suitable location.
    """
    if not user:
        return {"expires": None}

    now = timezone.now()
    if "cyberstorm_beta_access" in UserFlag.get_active_flags_on_user(user, now):
        return {"expires": (now + datetime.timedelta(weeks=4))}

    return {"expires": None}
