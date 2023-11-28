import json

from django.db.models import Q, QuerySet
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import ListAPIView, RetrieveAPIView, get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.account.models.service_account import ServiceAccount
from thunderstore.api.cyberstorm.serializers import (
    CyberstormServiceAccountSerializer,
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
                        "teamName": team.name,
                    }
                ),
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)


class AddTeamMemberAPIView(APIView):
    def post(self, request, format=None):
        form = AddTeamMemberForm(
            user=request.user,
            data=request.data,
        )

        if form.is_valid():
            form.save()
            return Response(
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)


class RemoveTeamMemberAPIView(APIView):
    def post(self, request, format=None):
        form = RemoveTeamMemberForm(
            user=request.user,
            data=request.data,
        )

        if form.is_valid():
            form.save()
            return Response(
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)


class EditTeamMemberAPIView(APIView):
    def post(self, request, format=None):
        form = EditTeamMemberForm(
            user=request.user,
            data=request.data,
        )

        if form.is_valid():
            form.save()
            return Response(
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)


class DisbandTeamAPIView(APIView):
    def post(self, request, format=None):
        form = DisbandTeamForm(
            user=request.user,
            data=request.data,
        )

        if form.is_valid():
            form.save()
            return Response(
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)


class DonationLinkTeamAPIView(APIView):
    def post(self, request, team_id, format=None):
        try:
            print(team_id)
            print(request.data)
            team = Team.objects.get(name=team_id)
        except Team.DoesNotExist:
            return Response(
                json.dumps(
                    {
                        "error": "Team",
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
                status=status.HTTP_201_CREATED,
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
