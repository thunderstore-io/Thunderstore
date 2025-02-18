from django.db.models import Q, QuerySet
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import (
    CreateAPIView,
    DestroyAPIView,
    ListAPIView,
    RetrieveAPIView,
    get_object_or_404,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.account.models.service_account import ServiceAccount
from thunderstore.api.cyberstorm.serializers import (
    CyberstormCreateTeamSerializer,
    CyberstormServiceAccountSerializer,
    CyberstormTeamAddMemberRequestSerializer,
    CyberstormTeamAddMemberResponseSerializer,
    CyberstormTeamMemberSerializer,
    CyberstormTeamSerializer,
)
from thunderstore.api.ordering import StrictOrderingFilter
from thunderstore.api.utils import (
    CyberstormAutoSchemaMixin,
    conditional_swagger_auto_schema,
)
from thunderstore.repository.forms import AddTeamMemberForm
from thunderstore.repository.models import TeamMemberRole
from thunderstore.repository.models.team import Team, TeamMember


class TeamPermissionsMixin:
    permission_classes = [IsAuthenticated]

    def _get_team_object(self) -> Team:
        teams = Team.objects.exclude(is_active=False)
        team_identifier = self.kwargs.get("team_id") or self.kwargs.get("team_name")
        return get_object_or_404(teams, name__iexact=team_identifier)

    def check_permissions(self, request: Request) -> None:
        super().check_permissions(request)
        team = self._get_team_object()
        if not team.can_user_access(request.user):
            raise PermissionDenied("You do not have permission to access this team.")


class TeamAPIView(CyberstormAutoSchemaMixin, RetrieveAPIView):
    serializer_class = CyberstormTeamSerializer
    queryset = Team.objects.exclude(is_active=False)
    lookup_field = "name__iexact"
    lookup_url_kwarg = "team_id"


class TeamRestrictedAPIView(TeamPermissionsMixin, ListAPIView):
    pass


class TeamCreateAPIView(CreateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Team.objects.exclude(is_active=False)
    serializer_class = CyberstormCreateTeamSerializer

    def _create_team(self, name: str) -> Team:
        team = Team.objects.create(name=name)
        team.add_member(user=self.request.user, role=TeamMemberRole.owner)
        return team

    def perform_create(self, serializer) -> None:
        team_name = serializer.validated_data["name"]
        instance = self._create_team(team_name)
        serializer.instance = instance

    @conditional_swagger_auto_schema(
        request_body=serializer_class,
        responses={201: serializer_class},
        operation_id="cyberstorm.team.create",
        tags=["cyberstorm"],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class TeamMemberListAPIView(CyberstormAutoSchemaMixin, TeamRestrictedAPIView):
    serializer_class = CyberstormTeamMemberSerializer
    filter_backends = [StrictOrderingFilter]
    ordering = ["-role", "user__username"]

    def get_queryset(self) -> QuerySet[TeamMember]:
        return (
            TeamMember.objects.real_users()
            .exclude(~Q(team__name__iexact=self.kwargs["team_id"]))
            .prefetch_related("user__social_auth")
        )


class TeamMemberAddAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @conditional_swagger_auto_schema(
        request_body=CyberstormTeamAddMemberRequestSerializer,
        responses={200: CyberstormTeamAddMemberResponseSerializer},
        operation_id="cyberstorm.team.member.add",
        tags=["cyberstorm"],
    )
    def post(self, request, team_name, format=None):
        team = get_object_or_404(Team, name__iexact=team_name)
        serializer = CyberstormTeamAddMemberRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        form = AddTeamMemberForm(
            user=request.user,
            data={
                **serializer.validated_data,
                "team": team.pk,
                "user": serializer.validated_data["username"],
            },
        )

        if form.is_valid():
            team_member = form.save()
            return Response(CyberstormTeamAddMemberResponseSerializer(team_member).data)
        else:
            raise ValidationError(form.errors)


class TeamServiceAccountListAPIView(CyberstormAutoSchemaMixin, TeamRestrictedAPIView):
    serializer_class = CyberstormServiceAccountSerializer
    filter_backends = [StrictOrderingFilter]
    ordering = ["user__first_name"]

    def get_queryset(self) -> QuerySet[ServiceAccount]:
        return ServiceAccount.objects.exclude(
            ~Q(owner__name__iexact=self.kwargs["team_id"]),
        ).select_related("user")


class DisbandTeamAPIView(TeamPermissionsMixin, DestroyAPIView):
    queryset = Team.objects.all()
    lookup_url_kwarg = "team_name"
    lookup_field = "name__iexact"

    def check_permissions(self, request):
        super().check_permissions(request)
        team = self.get_object()
        if not team.can_user_disband(request.user):
            raise PermissionDenied("You do not have permission to disband this team.")

    @conditional_swagger_auto_schema(
        operation_id="cyberstorm.team.disband",
        tags=["cyberstorm"],
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)
