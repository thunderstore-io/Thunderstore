import json

from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView, get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.account.models.service_account import ServiceAccount
from thunderstore.api.cyberstorm.serializers import (
    CyberstormServiceAccountSerializer,
    CyberstormTeamMemberSerializer,
    CyberstormTeamSerializer,
)
from thunderstore.api.cyberstorm.serializers.team import CyberstormTeamNameSerialiazer
from thunderstore.api.cyberstorm.serializers.user import CyberstormUsernameSerialiazer
from thunderstore.api.ordering import StrictOrderingFilter
from thunderstore.api.utils import CyberstormAutoSchemaMixin
from thunderstore.repository.forms import AddTeamMemberForm
from thunderstore.repository.models.team import Team, TeamMember

User = get_user_model()


class TeamDetailAPIView(CyberstormAutoSchemaMixin, RetrieveAPIView):
    serializer_class = CyberstormTeamSerializer
    queryset = Team.objects.exclude(is_active=False)
    lookup_field = "name__iexact"
    lookup_url_kwarg = "team_id"


class TeamRestrictedAPIView(ListAPIView):
    """
    Ensure the user is a member of the Team.
    """

    permission_classes = [IsAuthenticated]

    def check_permissions(self, request: Request) -> None:
        super().check_permissions(request)

        teams = Team.objects.exclude(is_active=False)
        team = get_object_or_404(teams, name__iexact=self.kwargs["team_id"])

        if not team.can_user_access(request.user):
            raise PermissionDenied()


class TeamMembersAPIView(CyberstormAutoSchemaMixin, TeamRestrictedAPIView):
    serializer_class = CyberstormTeamMemberSerializer
    filter_backends = [StrictOrderingFilter]
    ordering = ["-role", "user__username"]

    def get_queryset(self) -> QuerySet[TeamMember]:
        return (
            TeamMember.objects.real_users()
            .exclude(~Q(team__name__iexact=self.kwargs["team_id"]))
            .prefetch_related("user__social_auth")
        )


class CyberstormTeamAddMemberRequestSerialiazer(serializers.ModelSerializer):
    user = serializers.CharField()

    class Meta:
        model = TeamMember
        fields = ["user", "role"]


class CyberstormTeamAddMemberResponseSerialiazer(serializers.ModelSerializer):
    user = CyberstormUsernameSerialiazer()
    team = CyberstormTeamNameSerialiazer()

    class Meta:
        model = TeamMember
        fields = ["user", "team", "role"]


class AddTeamMemberAPIView(APIView):
    @swagger_auto_schema(
        request_body=CyberstormTeamAddMemberRequestSerialiazer,
        responses={200: CyberstormTeamAddMemberResponseSerialiazer},
        operation_id="cyberstorm.team.members.add",
        tags=["cyberstorm"],
    )
    def post(self, request, team_name, format=None):
        try:
            team = Team.objects.get(name=team_name)
        except Team.DoesNotExist:
            return Response(
                json.dumps(
                    {
                        "error": "Team not found",
                    }
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = CyberstormTeamAddMemberRequestSerialiazer(data=request.data)
        serializer.is_valid(raise_exception=True)

        form = AddTeamMemberForm(
            user=request.user,
            data={
                "team": team.pk,
                "user": serializer.validated_data["user"],
                "role": serializer.validated_data["role"],
            },
        )

        if form.is_valid():
            team_member = form.save()
            return Response(
                JSONRenderer().render(
                    CyberstormTeamAddMemberResponseSerialiazer(team_member).data
                ),
                status=status.HTTP_200_OK,
            )
        else:
            raise ValidationError(form.errors)


class TeamServiceAccountsAPIView(CyberstormAutoSchemaMixin, TeamRestrictedAPIView):
    serializer_class = CyberstormServiceAccountSerializer
    filter_backends = [StrictOrderingFilter]
    ordering = ["user__first_name"]

    def get_queryset(self) -> QuerySet[ServiceAccount]:
        return ServiceAccount.objects.exclude(
            ~Q(owner__name__iexact=self.kwargs["team_id"]),
        ).select_related("user")
