import datetime
from typing import List, Optional, Set, TypedDict

from django.db.models import Q, Value
from django.db.models.functions import Concat
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from pydantic import BaseModel
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.account.models.user_flag import UserFlag
from thunderstore.core.types import UserType
from thunderstore.repository.models import TeamMember
from thunderstore.social.utils import get_connection_avatar_url


class CurrentUserExperimentalApiView(APIView):
    """
    Gets information about the current user, such as rated packages and permissions
    """

    permission_classes = [AllowAny]

    @swagger_auto_schema(tags=["experimental"])
    def get(self, request, format=None):
        if request.user.is_authenticated:
            profile = get_user_profile(request.user)
        else:
            profile = get_empty_profile()

        return Response(profile)


class SocialAuthConnection(TypedDict):
    provider: str
    username: str
    avatar: Optional[str]


class SocialAuthConnectionSerializer(serializers.Serializer):
    provider = serializers.CharField()
    username = serializers.CharField()
    avatar = serializers.CharField()


class SubscriptionStatus(TypedDict):
    expires: Optional[datetime.datetime]


class SubscriptionStatusSerializer(serializers.Serializer):
    expires = serializers.DateTimeField()


class UserTeam(BaseModel):
    name: str
    role: str
    member_count: int


class UserTeamSerializer(serializers.Serializer):
    name = serializers.CharField()
    role = serializers.CharField()
    member_count = serializers.IntegerField(min_value=0)


class UserProfile(TypedDict):
    username: Optional[str]
    capabilities: Set[str]
    connections: List[SocialAuthConnection]
    subscription: SubscriptionStatus
    rated_packages: List[str]
    teams: List[str]
    teams_full: List[UserTeam]


class UserProfileSerializer(serializers.Serializer):
    username = serializers.CharField()
    capabilities = serializers.ListField()
    connections = SocialAuthConnectionSerializer(many=True)
    subscription = SubscriptionStatusSerializer()
    rated_packages = serializers.ListField()
    rated_packages_cyberstorm = serializers.ListField()
    teams = (
        serializers.ListField()
    )  # This is in active use by the Django frontend react components at least
    teams_full = UserTeamSerializer(many=True)


def get_empty_profile() -> UserProfile:
    return {
        "username": None,
        "capabilities": set(),
        "connections": [],
        "subscription": get_subscription_status(user=None),
        "rated_packages": [],
        "rated_packages_cyberstorm": [],
        "teams": [],
        "teams_full": [],
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

    rated_packages_cyberstorm = list(
        user.package_ratings.select_related("package")
        .annotate(P=Concat("package__namespace__name", Value("-"), "package__name"))
        .values_list(
            "P",
            flat=True,
        )
    )

    teams = get_teams(user)

    return UserProfileSerializer(
        {
            "username": username,
            "capabilities": capabilities,
            "connections": get_social_auth_connections(user),
            "subscription": get_subscription_status(user),
            "rated_packages": rated_packages,
            "rated_packages_cyberstorm": rated_packages_cyberstorm,
            "teams": [x.name for x in teams],
            "teams_full": teams,
        }
    ).data


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


OAUTH_USERNAME_FIELDS = {
    "discord": "username",
    "github": "login",
    "overwolf": "nickname",
}


def get_social_auth_connections(user: UserType) -> List[SocialAuthConnection]:
    """
    Return information regarding user's registered OAuth logins.
    """

    return [
        {
            "provider": sa.provider,
            "username": sa.extra_data.get(OAUTH_USERNAME_FIELDS.get(sa.provider)),
            "avatar": get_connection_avatar_url(sa),
        }
        for sa in user.social_auth.all()
    ]


def get_teams(user: UserType) -> List[UserTeam]:
    """
    Return information regarding the teams the user belongs to.
    """
    memberships = (
        TeamMember.objects.prefetch_related(
            "team__members__user__service_account",
        )
        .exclude(team__is_active=False)
        .exclude(~Q(user=user))
    )

    return [
        UserTeam(
            name=membership.team.name,
            role=membership.role,
            member_count=len(
                [
                    m
                    for m in membership.team.members.all()
                    if not hasattr(m.user, "service_account")
                ],
            ),
        )
        for membership in memberships.all()
    ]
