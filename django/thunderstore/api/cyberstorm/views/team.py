from django.db.models import Q, QuerySet
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView, get_object_or_404
from rest_framework.permissions import AllowAny
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
from thunderstore.api.utils import (
    CyberstormAutoSchemaMixin,
    conditional_swagger_auto_schema,
)
from thunderstore.repository.forms import AddTeamMemberForm
from thunderstore.repository.models.team import Team, TeamMember


class TeamAPIView(CyberstormAutoSchemaMixin, RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = CyberstormTeamSerializer
    queryset = Team.objects.exclude(is_active=False)
    lookup_field = "name__iexact"
    lookup_url_kwarg = "team_id"


class TeamRestrictedAPIView(ListAPIView):
    """
    Ensure the user is a member of the Team.
    """

    def check_permissions(self, request: Request) -> None:
        super().check_permissions(request)

        teams = Team.objects.exclude(is_active=False)
        team = get_object_or_404(teams, name__iexact=self.kwargs["team_id"])

        if not team.can_user_access(request.user):
            raise PermissionDenied()


class TeamMemberListAPIView(CyberstormAutoSchemaMixin, TeamRestrictedAPIView):
    permission_classes = [AllowAny]
    serializer_class = CyberstormTeamMemberSerializer
    filter_backends = [StrictOrderingFilter]
    ordering = ["-role", "user__username"]

    def get_queryset(self) -> QuerySet[TeamMember]:
        return (
            TeamMember.objects.real_users()
            .exclude(~Q(team__name__iexact=self.kwargs["team_id"]))
            .prefetch_related("user__social_auth")
        )


class CyberstormTeamAddMemberRequestSerialiazer(serializers.Serializer):
    username = serializers.CharField()
    role = serializers.ChoiceField(
        choices=AddTeamMemberForm.base_fields["role"].choices
    )


class CyberstormTeamAddMemberResponseSerialiazer(serializers.Serializer):
    username = serializers.CharField(source="user")
    role = serializers.CharField()
    team = serializers.CharField()


class TeamMemberAddAPIView(APIView):
    @conditional_swagger_auto_schema(
        request_body=CyberstormTeamAddMemberRequestSerialiazer,
        responses={200: CyberstormTeamAddMemberResponseSerialiazer},
        operation_id="cyberstorm.team.member.add",
        tags=["cyberstorm"],
    )
    def post(self, request, team_name, format=None):
        team = get_object_or_404(Team, name__iexact=team_name)
        serializer = CyberstormTeamAddMemberRequestSerialiazer(data=request.data)
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
            return Response(
                CyberstormTeamAddMemberResponseSerialiazer(team_member).data
            )
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
