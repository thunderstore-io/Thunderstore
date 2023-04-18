from django.contrib.auth import SESSION_KEY, get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.utils import timezone
from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication as DRFTokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

from thunderstore.account.models import ServiceAccount
from thunderstore.account.tokens import hash_service_account_api_token

User = get_user_model()


class ServiceAccountTokenAuthentication(DRFTokenAuthentication):
    """
    Authenticate with bearer token matching ServiceAccount's api_token
    """

    keyword = "Bearer"

    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION")

        if header is None or not header.startswith("Bearer "):
            return None

        token = header[7:]
        hashed = hash_service_account_api_token(token)

        try:
            sa = ServiceAccount.objects.select_related("user").get(api_token=hashed)
        except ServiceAccount.DoesNotExist:
            raise AuthenticationFailed("Invalid Service Account token")

        sa.last_used = timezone.now()
        sa.save(update_fields=("last_used",))

        return (sa.user, token)


class UserSessionTokenAuthentication(DRFTokenAuthentication):
    """
    This authentication is used for the Django React transition only.

    This uses the session ID prepended by "Session ". For example:
    `Authorization: Session cu5zafrhapnck64nsyz7cl9w6ezwuuz4`
    """

    keyword = "Session"

    def authenticate_credentials(self, key):
        session = SessionStore(session_key=key)
        if not session.exists(key):
            raise exceptions.AuthenticationFailed("Invalid token.")
        user_id = session.get(SESSION_KEY)
        if user_id is None:
            raise exceptions.AuthenticationFailed("Invalid token.")
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed("User inactive or deleted.")
        if not user.is_active:
            raise exceptions.AuthenticationFailed("User inactive or deleted.")

        return (user, key)
