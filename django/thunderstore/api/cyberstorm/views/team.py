from django.db.models import Q, QuerySet
from django.http import HttpRequest
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView, get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.account.forms import (
    CreateServiceAccountForm,
    DeleteServiceAccountForm,
)
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
from thunderstore.repository.forms import (
    AddTeamMemberForm,
    CreateTeamForm,
    DisbandTeamForm,
    DonationLinkTeamForm,
    EditTeamMemberForm,
    RemoveTeamMemberForm,
)
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


class CyberstormEditTeamRequestSerialiazer(serializers.Serializer):
    donation_link = serializers.CharField(
        max_length=Team._meta.get_field("donation_link").max_length,
        validators=Team._meta.get_field("donation_link").validators,
    )


class CyberstormEditTeamResponseSerialiazer(serializers.Serializer):
    donation_link = serializers.CharField()


class EditTeamAPIView(APIView):
    @conditional_swagger_auto_schema(
        request_body=CyberstormEditTeamRequestSerialiazer,
        responses={200: CyberstormEditTeamResponseSerialiazer},
        operation_id="cyberstorm.team.edit",
        tags=["cyberstorm"],
    )
    def post(self, request: HttpRequest, team_name: str):
        serializer = CyberstormEditTeamRequestSerialiazer(data=request.data)
        serializer.is_valid(raise_exception=True)
        team = get_object_or_404(Team, name__iexact=team_name)
        form = DonationLinkTeamForm(
            user=request.user,
            instance=team,
            data=serializer.validated_data,
        )

        if form.is_valid():
            team = form.save()
            return Response(CyberstormEditTeamResponseSerialiazer(team).data)
        else:
            raise ValidationError(form.errors)


class CyberstormTeamCreateRequestSerialiazer(serializers.Serializer):
    name = serializers.CharField(
        max_length=Team._meta.get_field("name").max_length,
        validators=Team._meta.get_field("name").validators,
    )


class CyberstormTeamCreateResponseSerialiazer(serializers.Serializer):
    name = serializers.CharField()


class TeamCreateAPIView(APIView):
    @conditional_swagger_auto_schema(
        request_body=CyberstormTeamCreateRequestSerialiazer,
        responses={200: CyberstormTeamCreateResponseSerialiazer},
        operation_id="cyberstorm.teams.create",
        tags=["cyberstorm"],
    )
    def post(self, request: HttpRequest):
        serializer = CyberstormTeamCreateRequestSerialiazer(data=request.data)
        serializer.is_valid(raise_exception=True)

        form = CreateTeamForm(
            user=request.user,
            data=serializer.validated_data,
        )

        if form.is_valid():
            team = form.save()
            return Response(CyberstormTeamCreateResponseSerialiazer(team).data)
        else:
            raise ValidationError(form.errors)


class CyberstormDisbandTeamRequestSerialiazer(serializers.Serializer):
    verification = serializers.CharField()


class CyberstormDisbandTeamResponseSerialiazer(serializers.Serializer):
    name = serializers.CharField()


class DisbandTeamAPIView(APIView):
    @conditional_swagger_auto_schema(
        request_body=CyberstormDisbandTeamRequestSerialiazer,
        responses={200: CyberstormDisbandTeamResponseSerialiazer},
        operation_id="cyberstorm.team.disband",
        tags=["cyberstorm"],
    )
    def post(self, request: HttpRequest, team_name: str):
        serializer = CyberstormDisbandTeamRequestSerialiazer(data=request.data)
        serializer.is_valid(raise_exception=True)

        team = get_object_or_404(Team, name__iexact=team_name)

        form = DisbandTeamForm(
            user=request.user,
            instance=team,
            data=serializer.validated_data,
        )

        if form.is_valid():
            form.save()
            return Response(
                CyberstormDisbandTeamResponseSerialiazer({"name": team_name}).data
            )
        else:
            raise ValidationError(form.errors)


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


class CyberstormRemoveTeamMemberRequestSerialiazer(serializers.Serializer):
    username = serializers.CharField()


class CyberstormRemoveTeamMemberResponseSerialiazer(serializers.Serializer):
    username = serializers.CharField()
    team_name = serializers.CharField()


class RemoveTeamMemberAPIView(APIView):
    @conditional_swagger_auto_schema(
        request_body=CyberstormRemoveTeamMemberRequestSerialiazer,
        responses={200: CyberstormRemoveTeamMemberResponseSerialiazer},
        operation_id="cyberstorm.team.members.remove",
        tags=["cyberstorm"],
    )
    def post(self, request: HttpRequest, team_name: str):
        team = get_object_or_404(Team, name__iexact=team_name)

        serializer = CyberstormRemoveTeamMemberRequestSerialiazer(data=request.data)
        serializer.is_valid(raise_exception=True)

        team_member = get_object_or_404(
            TeamMember,
            user__username__iexact=serializer.validated_data["username"],
            team=team,
        )

        membership = team.get_membership_for_user(team_member.user)

        form = RemoveTeamMemberForm(
            user=request.user,
            data={"membership": membership},
        )

        if form.is_valid():
            form.save()
            return Response(
                CyberstormRemoveTeamMemberResponseSerialiazer(
                    {
                        "username": serializer.validated_data["username"],
                        "team_name": team_name,
                    }
                ).data
            )
        else:
            raise ValidationError(form.errors)


class CyberstormEditTeamMemberRequestSerialiazer(serializers.Serializer):
    username = serializers.CharField()
    role = serializers.ChoiceField(
        choices=EditTeamMemberForm.base_fields["role"].choices
    )


class CyberstormEditTeamMemberResponseSerialiazer(serializers.Serializer):
    username = serializers.CharField(source="user")
    role = serializers.ChoiceField(
        choices=EditTeamMemberForm.base_fields["role"].choices
    )
    team_name = serializers.CharField(source="team")


class EditTeamMemberAPIView(APIView):
    @conditional_swagger_auto_schema(
        request_body=CyberstormEditTeamMemberRequestSerialiazer,
        responses={200: CyberstormEditTeamMemberResponseSerialiazer},
        operation_id="cyberstorm.team.members.edit",
        tags=["cyberstorm"],
    )
    def post(self, request: HttpRequest, team_name: str):
        serializer = CyberstormEditTeamMemberRequestSerialiazer(data=request.data)
        serializer.is_valid(raise_exception=True)
        team_member = get_object_or_404(
            TeamMember,
            user__username__iexact=request.data["username"],
            team__name__iexact=team_name,
        )
        form = EditTeamMemberForm(
            user=request.user,
            instance=team_member,
            data=serializer.validated_data,
        )

        if form.is_valid():
            team_member = form.save()
            return Response(
                CyberstormEditTeamMemberResponseSerialiazer(team_member).data
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


class TeamCreateServiceAccountRequestSerialiazer(serializers.Serializer):
    nickname = serializers.CharField()


class TeamCreateServiceAccountResponseSerialiazer(serializers.Serializer):
    nickname = serializers.CharField()
    team_name = serializers.CharField()
    api_token = serializers.CharField()


class TeamCreateServiceAccountAPIView(APIView):
    @conditional_swagger_auto_schema(
        request_body=TeamCreateServiceAccountRequestSerialiazer,
        responses={200: TeamCreateServiceAccountResponseSerialiazer},
        operation_id="cyberstorm.team.service-account.create",
        tags=["cyberstorm"],
    )
    def post(self, request: HttpRequest, team_name: str):
        serializer = TeamCreateServiceAccountRequestSerialiazer(data=request.data)
        serializer.is_valid(raise_exception=True)
        team = get_object_or_404(Team, name__iexact=team_name)
        form = CreateServiceAccountForm(
            user=request.user,
            data={
                **serializer.validated_data,
                "team": team,
            },
        )

        if form.is_valid():
            service_account = form.save()
            return Response(
                TeamCreateServiceAccountResponseSerialiazer(
                    {
                        "nickname": service_account.nickname,
                        "team_name": service_account.owner.name,
                        "api_token": form.api_token,
                    }
                ).data
            )
        else:
            raise ValidationError(form.errors)


class TeamDeleteServiceAccountRequestSerialiazer(serializers.Serializer):
    service_account_uuid = serializers.CharField()


class TeamDeleteServiceAccountResponseSerialiazer(serializers.Serializer):
    detail = serializers.CharField()


class TeamDeleteServiceAccountAPIView(APIView):
    @conditional_swagger_auto_schema(
        request_body=TeamDeleteServiceAccountRequestSerialiazer,
        responses={200: TeamDeleteServiceAccountResponseSerialiazer},
        operation_id="cyberstorm.team.service-account.delete",
        tags=["cyberstorm"],
    )
    def post(self, request: HttpRequest, team_name: str):
        serializer = TeamDeleteServiceAccountRequestSerialiazer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service_account = get_object_or_404(
            ServiceAccount,
            owner__name__iexact=team_name,
            uuid=serializer.validated_data["service_account_uuid"],
        )
        form = DeleteServiceAccountForm(
            user=request.user,
            data={"service_account": service_account},
        )

        if form.is_valid():
            form.save()
            return Response({"detail": "Service account deleted"})
        else:
            raise ValidationError(form.errors)
