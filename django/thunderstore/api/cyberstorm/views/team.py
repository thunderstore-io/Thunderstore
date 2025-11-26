from django.db.models import Q, QuerySet
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView, get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.account.models.service_account import ServiceAccount
from thunderstore.api.cyberstorm.serializers import (
    CyberstormCreateServiceAccountSerializer,
    CyberstormCreateTeamSerializer,
    CyberstormServiceAccountSerializer,
    CyberstormTeamAddMemberRequestSerializer,
    CyberstormTeamAddMemberResponseSerializer,
    CyberstormTeamMemberSerializer,
    CyberstormTeamMemberUpdateSerializer,
    CyberstormTeamSerializer,
    CyberstormTeamUpdateSerializer,
)
from thunderstore.api.cyberstorm.services.team import (
    create_service_account,
    create_team,
    delete_service_account,
    disband_team,
    remove_team_member,
    update_team,
    update_team_member,
)
from thunderstore.api.ordering import StrictOrderingFilter
from thunderstore.api.utils import (
    CyberstormAutoSchemaMixin,
    conditional_swagger_auto_schema,
)
from thunderstore.repository.forms import AddTeamMemberForm
from thunderstore.repository.models.team import Team, TeamMember


class TeamPermissionsMixin:
    permission_classes = [IsAuthenticated]

    def _get_team_object(self) -> Team:
        teams = Team.objects.exclude(is_active=False)
        team_identifier = self.kwargs.get("team_id") or self.kwargs.get("team_name")
        return get_object_or_404(teams, name=team_identifier)

    def check_permissions(self, request: Request) -> None:
        super().check_permissions(request)
        team = self._get_team_object()
        if not team.can_user_access(request.user):
            raise PermissionDenied("You do not have permission to access this team.")


class TeamAPIView(CyberstormAutoSchemaMixin, RetrieveAPIView):
    serializer_class = CyberstormTeamSerializer
    queryset = Team.objects.exclude(is_active=False)
    lookup_field = "name"
    lookup_url_kwarg = "team_id"

    def retrieve(self, *args, **kwargs):
        response = super().retrieve(*args, **kwargs)
        response["Cache-Control"] = "public, max-age=60"
        return response


class TeamRestrictedAPIView(TeamPermissionsMixin, ListAPIView):
    pass


class TeamCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @conditional_swagger_auto_schema(
        request_body=CyberstormCreateTeamSerializer,
        responses={201: CyberstormTeamSerializer},
        operation_id="cyberstorm.team.create",
        tags=["cyberstorm"],
    )
    def post(self, request, *args, **kwargs):
        serializer = CyberstormCreateTeamSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        team_name = serializer.validated_data["name"]
        team = create_team(agent=request.user, team_name=team_name)

        return_data = CyberstormTeamSerializer(team).data
        return Response(return_data, status=status.HTTP_201_CREATED)


class TeamMemberListAPIView(CyberstormAutoSchemaMixin, TeamRestrictedAPIView):
    serializer_class = CyberstormTeamMemberSerializer
    filter_backends = [StrictOrderingFilter]
    ordering = ["-role", "user__username"]

    def get_queryset(self) -> QuerySet[TeamMember]:
        return (
            TeamMember.objects.real_users()
            .exclude(~Q(team__name=self.kwargs["team_id"]))
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
        team = get_object_or_404(Team, name=team_name)
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


class TeamMemberRemoveAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @conditional_swagger_auto_schema(
        request_body=None,
        responses={204: ""},
        operation_id="cyberstorm.team.member.remove",
        tags=["cyberstorm"],
    )
    def delete(self, request, team_name, username):
        team = get_object_or_404(Team, name=team_name)
        member = get_object_or_404(
            TeamMember.objects.real_users().select_related("user"),
            team=team,
            user__username=username,
        )

        remove_team_member(agent=request.user, member=member)

        return Response(status=status.HTTP_204_NO_CONTENT)


class TeamServiceAccountListAPIView(CyberstormAutoSchemaMixin, TeamRestrictedAPIView):
    serializer_class = CyberstormServiceAccountSerializer
    filter_backends = [StrictOrderingFilter]
    ordering = ["user__first_name"]

    def get_queryset(self) -> QuerySet[ServiceAccount]:
        return ServiceAccount.objects.exclude(
            ~Q(owner__name=self.kwargs["team_id"]),
        ).select_related("user")


class DisbandTeamAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @conditional_swagger_auto_schema(
        operation_id="cyberstorm.team.disband",
        tags=["cyberstorm"],
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def delete(self, request, *args, **kwargs):
        team = get_object_or_404(Team, name=kwargs["team_name"])
        disband_team(agent=request.user, team=team)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CreateServiceAccountAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @conditional_swagger_auto_schema(
        request_body=CyberstormCreateServiceAccountSerializer,
        operation_id="cyberstorm.team.service-account.create",
        tags=["cyberstorm"],
        responses={status.HTTP_201_CREATED: CyberstormCreateServiceAccountSerializer},
    )
    def post(self, request, *args, **kwargs):
        serializer = CyberstormCreateServiceAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        team = get_object_or_404(Team, name=kwargs["team_name"])

        service_account, token = create_service_account(
            agent=request.user,
            team=team,
            nickname=serializer.validated_data["nickname"],
        )

        response_data = {
            "nickname": service_account.nickname,
            "team_name": service_account.owner.name,
            "api_token": token,
        }

        return Response(response_data, status=status.HTTP_201_CREATED)


class DeleteServiceAccountAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @conditional_swagger_auto_schema(
        request_body=None,
        operation_id="cyberstorm.service-account.delete",
        tags=["cyberstorm"],
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def delete(self, request, *args, **kwargs):
        service_account = get_object_or_404(ServiceAccount, uuid=kwargs["uuid"])
        delete_service_account(agent=request.user, service_account=service_account)
        return Response(status=status.HTTP_204_NO_CONTENT)


class UpdateTeamAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CyberstormTeamUpdateSerializer
    http_method_names = ["patch"]

    @conditional_swagger_auto_schema(
        operation_id="cyberstorm.team.update",
        tags=["cyberstorm"],
        request_body=CyberstormTeamUpdateSerializer,
        responses={status.HTTP_200_OK: serializer_class},
    )
    def patch(self, request, team_name, *args, **kwargs):
        team = get_object_or_404(Team.objects.exclude(is_active=False), name=team_name)

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_team = update_team(
            agent=request.user,
            team=team,
            donation_link=serializer.validated_data["donation_link"],
        )

        return_data = self.serializer_class(instance=updated_team).data
        return Response(return_data, status=status.HTTP_200_OK)


class UpdateTeamMemberAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CyberstormTeamMemberUpdateSerializer
    http_method_names = ["patch"]

    @conditional_swagger_auto_schema(
        operation_id="cyberstorm.team.member.update",
        tags=["cyberstorm"],
        request_body=CyberstormTeamMemberUpdateSerializer,
        responses={status.HTTP_200_OK: serializer_class},
    )
    def patch(self, request, *args, **kwargs):
        team_member = get_object_or_404(
            TeamMember.objects.real_users(),
            team__name=self.kwargs["team_name"],
            user__username=self.kwargs["team_member"],
        )

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        team_member = update_team_member(
            agent=request.user,
            team_member=team_member,
            role=serializer.validated_data["role"],
        )

        serializer = self.serializer_class(instance=team_member)
        return Response(serializer.data, status=status.HTTP_200_OK)
