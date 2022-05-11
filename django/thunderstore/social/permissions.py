from abc import abstractmethod

from django.conf import settings
from rest_framework.exceptions import APIException, AuthenticationFailed
from rest_framework.permissions import BasePermission


class ImproperlyConfigured(APIException):
    default_code = "improperly_configured"
    default_detail = "Server is improperly configured"
    status_code = 500


class SharedSecretPermission(BasePermission):
    """
    Compares secret received in a header to one configured on the server.

    Should be used for rudimentary access validation for endpoints that
    are called by another one of our servers that has no access to user
    credentials.
    """

    @property
    @abstractmethod
    def SHARED_SECRET(self) -> str:
        """
        Local value, against which the submitted value is checked.
        """

    def has_permission(self, request, view) -> bool:
        if not self.SHARED_SECRET:
            raise ImproperlyConfigured

        header = request.META.get("HTTP_AUTHORIZATION")

        if header is None or header != f"TS-Secret {self.SHARED_SECRET}":
            raise AuthenticationFailed

        return True


class OauthSharedSecretPermission(SharedSecretPermission):
    """
    For completing OAuth login.
    """

    SHARED_SECRET = settings.OAUTH_SHARED_SECRET
