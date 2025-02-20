from django.http import HttpRequest
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import CreateAPIView, DestroyAPIView, get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from thunderstore.account.models import ServiceAccount
from thunderstore.api.cyberstorm.serializers.service_account import (
    CreateServiceAccountSerializer,
)
from thunderstore.api.utils import conditional_swagger_auto_schema
from thunderstore.repository.models import Team


class TeamPermissionMixin:
    permission_classes = [IsAuthenticated]

    def dispatch(self, request, *args, **kwargs):
        self.team = self.get_team()
        return super().dispatch(request, *args, **kwargs)

    def get_team(self) -> Team:
        team_name = self.kwargs.get("team_name")
        return get_object_or_404(Team, name__iexact=team_name)

    def check_permissions(self, request: HttpRequest) -> None:
        super().check_permissions(request)
        self.check_user_team_permissions()

    def check_user_team_permissions(self) -> None:
        if not self.team.can_user_access(self.request.user):
            raise PermissionDenied("User does not have permission to access this team.")


class CreateServiceAccountAPIView(TeamPermissionMixin, CreateAPIView):
    queryset = ServiceAccount.objects.all()
    serializer_class = CreateServiceAccountSerializer

    def check_permissions(self, request: HttpRequest) -> None:
        super().check_permissions(request)
        if not self.team.can_user_create_service_accounts(request.user):
            raise PermissionDenied(
                "User does not have permission to create service accounts "
                "for this team."
            )

    def perform_create(self, serializer: CreateServiceAccountSerializer):
        nickname = serializer.validated_data["nickname"]
        service_account_data = self.create_service_account(nickname)
        serializer.instance = service_account_data

    def create_service_account(self, nickname: str):
        service_account, token = ServiceAccount.create(
            owner=self.team,
            nickname=nickname,
            creator=self.request.user,
        )

        return {
            "nickname": service_account.nickname,
            "team_name": service_account.owner.name,
            "api_token": token,
        }

    @conditional_swagger_auto_schema(
        request_body=serializer_class,
        responses={status.HTTP_201_CREATED: serializer_class},
        operation_id="cyberstorm.team.service-account.create",
        tags=["cyberstorm"],
    )
    def post(self, request, *args, **kwargs) -> Response:
        return super().post(request, *args, **kwargs)


class DeleteServiceAccountAPIView(TeamPermissionMixin, DestroyAPIView):
    queryset = ServiceAccount.objects.all()
    lookup_field = "uuid"

    def check_permissions(self, request: HttpRequest) -> None:
        super().check_permissions(request)
        if not self.team.can_user_delete_service_accounts(request.user):
            raise PermissionDenied(
                "User does not have permission to delete service accounts "
                "for this team."
            )

    @conditional_swagger_auto_schema(
        responses={status.HTTP_204_NO_CONTENT: ""},
        operation_id="cyberstorm.team.service-account.delete",
        tags=["cyberstorm"],
    )
    def delete(self, request, *args, **kwargs) -> Response:
        return super().delete(request, *args, **kwargs)
