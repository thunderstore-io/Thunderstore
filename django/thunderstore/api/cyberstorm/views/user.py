from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import DestroyAPIView
from rest_framework.permissions import IsAuthenticated
from social_django.models import UserSocialAuth

from thunderstore.api.utils import conditional_swagger_auto_schema

User = get_user_model()


@method_decorator(
    name="delete",
    decorator=conditional_swagger_auto_schema(
        responses={status.HTTP_204_NO_CONTENT: None},
        operation_id="cyberstorm.delete.user",
        tags=["cyberstorm"],
    ),
)
class DeleteUserAPIView(DestroyAPIView):
    queryset = User.objects.filter(is_active=True)
    lookup_field = "username__iexact"
    lookup_url_kwarg = "username"
    permission_classes = [IsAuthenticated]

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        if obj != request.user:
            raise PermissionDenied("Cannot delete other users.")


@method_decorator(
    name="delete",
    decorator=conditional_swagger_auto_schema(
        responses={status.HTTP_204_NO_CONTENT: None},
        operation_id="cyberstorm.disconnect.user.provider",
        tags=["cyberstorm"],
    ),
)
class DisconnectUserLinkedAccountAPIView(DestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = UserSocialAuth.objects.all()

    def check_permissions(self, request):
        super().check_permissions(request)
        username = self.kwargs["username"]
        target_user = get_object_or_404(User, username__iexact=username)
        if request.user != target_user:
            raise PermissionDenied("Cannot disconnect another user's account.")
        if target_user.social_auth.count() == 1:
            raise PermissionDenied("Cannot disconnect last linked auth method.")

    def get_object(self):
        provider = self.kwargs["provider"]
        username = self.kwargs["username"]
        obj = get_object_or_404(
            self.get_queryset(),
            user__username__iexact=username,
            provider__iexact=provider,
        )
        self.check_object_permissions(self.request, obj)
        return obj
