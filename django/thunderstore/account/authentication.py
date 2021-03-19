from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.utils import timezone
from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication as DRFTokenAuthentication
from rest_framework.authtoken.models import Token

from thunderstore.account.models import ServiceAccount

User = get_user_model()


class TokenAuthentication(DRFTokenAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        out = super().authenticate(request)
        if out is not None and all(out):
            # The request has been authenticated
            token: Token = out[1]
            service_account = ServiceAccount.objects.filter(user=token.user).first()
            if service_account:
                service_account.last_used = timezone.now()
                service_account.save(update_fields=("last_used",))
        return out


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
        user_id = session.get("_auth_user_id")
        if user_id is None:
            raise exceptions.AuthenticationFailed("Invalid token.")
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed("User inactive or deleted.")
        if not user.is_active:
            raise exceptions.AuthenticationFailed("User inactive or deleted.")

        return (user, None)
