import json

from django.db.models import Q, QuerySet
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import ListAPIView, RetrieveAPIView, get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.account.forms import (
    CreateServiceAccountForm,
    DeleteServiceAccountForm,
    EditServiceAccountForm,
)
from thunderstore.account.models.service_account import ServiceAccount
from thunderstore.api.cyberstorm.serializers import (
    CyberstormEditServiceAccountSerialiazer,
    CyberstormServiceAccountSerializer,
    CyberstormTeamAddMemberSerialiazer,
    CyberstormTeamCreateSerialiazer,
    CyberstormTeamMemberSerializer,
    CyberstormTeamSerializer,
)
from thunderstore.api.ordering import StrictOrderingFilter
from thunderstore.api.utils import CyberstormAutoSchemaMixin
from thunderstore.repository.forms import (
    AddTeamMemberForm,
    CreateTeamForm,
    DisbandTeamForm,
    DonationLinkTeamForm,
    EditTeamMemberForm,
    RemoveTeamMemberForm,
)
from thunderstore.repository.models.team import Team, TeamMember


class TeamCreateAPIView(APIView):
    @swagger_auto_schema(
        request_body=CyberstormTeamCreateSerialiazer,
        responses={200: ""},
        operation_id="cyberstorm.teams.create",
        tags=["cyberstorm"],
    )
    def post(self, request, format=None):
        form = CreateTeamForm(
            user=request.user,
            data=request.data,
        )

        if form.is_valid():
            team = form.save()
            return Response(
                json.dumps(
                    {
                        "team_name": team.name,
                    }
                ),
                status=status.HTTP_200_OK,
            )
        else:
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)


class AddTeamMemberAPIView(APIView):
    # TODO: Needs to the team as an field
    # And a membership as an instance, somehow?

    @swagger_auto_schema(
        request_body=CyberstormTeamAddMemberSerialiazer,
        responses={200: ""},
        operation_id="cyberstorm.team.members.add",
        tags=["cyberstorm"],
    )
    def post(self, request, team_id, format=None):
        try:
            team = Team.objects.get(name=team_id)
        except Team.DoesNotExist:
            return Response(
                json.dumps(
                    {
                        "error": "Team not found",
                    }
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )
        formData = {"team": team.pk}
        if "user" in request.data:
            formData["user"] = request.data["user"]
        if "role" in request.data:
            formData["role"] = request.data["role"]
        print(formData)
        form = AddTeamMemberForm(
            user=request.user,
            data=formData,
        )

        if form.is_valid():
            team_member = form.save()
            return Response(
                json.dumps(
                    {
                        "team_name": team_member.team.name,
                        "team_member": team_member.user.username,
                        "team_member_role": team_member.role,
                    }
                ),
                status=status.HTTP_200_OK,
            )
        else:
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)


class RemoveTeamMemberAPIView(APIView):

    # TODO: What? It wants a membership object?
    @swagger_auto_schema(
        request_body=CyberstormEditServiceAccountSerialiazer,
        responses={200: ""},
        operation_id="cyberstorm.team.service-account.edit",
        tags=["cyberstorm"],
    )
    def post(self, request, team_id, format=None):
        try:
            team = Team.objects.get(name=team_id)
        except Team.DoesNotExist:
            return Response(
                json.dumps(
                    {
                        "error": "Team not found",
                    }
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            team_member = TeamMember.objects.get(
                user__username=request.data["user"], team=team
            )
        except TeamMember.DoesNotExist:
            return Response(
                json.dumps(
                    {
                        "error": "Team member not found",
                    }
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )
        membership = team.get_membership_for_user(team_member.user)
        form = RemoveTeamMemberForm(
            user=request.user,
            data={"membership": membership},
        )

        if form.is_valid():
            form.save()
            return Response(
                status=status.HTTP_200_OK,
            )
        else:
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)


class EditTeamMemberAPIView(APIView):
    @swagger_auto_schema(
        request_body=CyberstormEditServiceAccountSerialiazer,
        responses={200: ""},
        operation_id="cyberstorm.team.service-account.edit",
        tags=["cyberstorm"],
    )
    def post(self, request, team_id, format=None):
        try:
            team_member = TeamMember.objects.get(user=request.user, team__id=team_id)
        except TeamMember.DoesNotExist:
            return Response(
                json.dumps(
                    {
                        "error": "Team member not found",
                    }
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )
        form = EditTeamMemberForm(
            user=request.user,
            instance=team_member,
            data=request.data,
        )

        if form.is_valid():
            form.save()
            return Response(
                status=status.HTTP_200_OK,
            )
        else:
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)


class DisbandTeamAPIView(APIView):
    @swagger_auto_schema(
        request_body=CyberstormEditServiceAccountSerialiazer,
        responses={200: ""},
        operation_id="cyberstorm.team.service-account.edit",
        tags=["cyberstorm"],
    )
    def post(self, request, team_id, format=None):
        try:
            team = Team.objects.get(name=team_id)
        except Team.DoesNotExist:
            return Response(
                json.dumps(
                    {
                        "error": "Team not found",
                    }
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )
        form = DisbandTeamForm(
            user=request.user,
            instance=team,
            data=request.data,
        )

        if form.is_valid():
            form.save()
            return Response(
                status=status.HTTP_200_OK,
            )
        else:
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)


class EditTeamAPIView(APIView):
    @swagger_auto_schema(
        request_body=CyberstormEditServiceAccountSerialiazer,
        responses={200: ""},
        operation_id="cyberstorm.team.service-account.edit",
        tags=["cyberstorm"],
    )
    def post(self, request, team_id, format=None):
        try:
            team = Team.objects.get(name=team_id)
        except Team.DoesNotExist:
            return Response(
                json.dumps(
                    {
                        "error": "Team not found",
                    }
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )
        form = DonationLinkTeamForm(
            user=request.user,
            instance=team,
            data=request.data,
        )

        if form.is_valid():
            form.save()
            return Response(
                status=status.HTTP_200_OK,
            )
        else:
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)


class CreateServiceAccountAPIView(APIView):
    @swagger_auto_schema(
        request_body=CyberstormEditServiceAccountSerialiazer,
        responses={200: ""},
        operation_id="cyberstorm.team.service-account.edit",
        tags=["cyberstorm"],
    )
    def post(self, request, team_id, format=None):
        try:
            team = Team.objects.get(id=team_id)
        except Team.DoesNotExist:
            return Response(
                json.dumps(
                    {
                        "error": "Team account not found",
                    }
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )
        form = CreateServiceAccountForm(
            user=request.user,
            data={"team": team, "nickname": request.data["nickname"]},
        )

        if form.is_valid():
            form.save()
            return Response(
                status=status.HTTP_200_OK,
            )
        else:
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)


class DeleteServiceAccountAPIView(APIView):
    @swagger_auto_schema(
        request_body=CyberstormEditServiceAccountSerialiazer,
        responses={200: ""},
        operation_id="cyberstorm.team.service-account.edit",
        tags=["cyberstorm"],
    )
    def post(self, request, team_id, service_account_uuid, format=None):
        try:
            service_account = ServiceAccount.objects.get(
                team__id=team_id, uuid=service_account_uuid
            )
        except ServiceAccount.DoesNotExist:
            return Response(
                json.dumps(
                    {
                        "error": "Service account not found",
                    }
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )
        form = DeleteServiceAccountForm(
            user=request.user,
            data={"service_account": service_account},
        )

        if form.is_valid():
            form.save()
            return Response(
                status=status.HTTP_200_OK,
            )
        else:
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)


class EditServiceAccountAPIView(APIView):
    @swagger_auto_schema(
        request_body=CyberstormEditServiceAccountSerialiazer,
        responses={200: ""},
        operation_id="cyberstorm.team.service-account.edit",
        tags=["cyberstorm"],
    )
    def post(self, request, team_id, service_account_uuid, format=None):
        try:
            service_account = ServiceAccount.objects.get(
                team__id=team_id, uuid=service_account_uuid
            )
        except ServiceAccount.DoesNotExist:
            return Response(
                json.dumps(
                    {
                        "error": "Service account not found",
                    }
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )
        form = EditServiceAccountForm(
            user=request.user,
            data={
                "service_account": service_account,
                "nickname": request.data["nickname"],
            },
        )

        if form.is_valid():
            form.save()
            return Response(
                status=status.HTTP_200_OK,
            )
        else:
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)


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


class TeamServiceAccountsAPIView(CyberstormAutoSchemaMixin, TeamRestrictedAPIView):
    serializer_class = CyberstormServiceAccountSerializer
    filter_backends = [StrictOrderingFilter]
    ordering = ["user__first_name"]

    def get_queryset(self) -> QuerySet[ServiceAccount]:
        return ServiceAccount.objects.exclude(
            ~Q(owner__name__iexact=self.kwargs["team_id"]),
        ).select_related("user")
