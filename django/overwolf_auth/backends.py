from typing import Any, Dict, Literal, Optional, TypedDict

from social_core.backends.oauth import BaseOAuth2  # type: ignore
from social_core.exceptions import AuthException  # type: ignore

from overwolf_auth.cached_jwk_client import decode_jwt

Response = Dict[str, Any]


class UserDetails(TypedDict):
    username: str
    email: str
    fullname: str
    first_name: str
    last_name: str


class OverwolfOAuth2(BaseOAuth2):
    """
    Overwolf OAuth 2 backend

    https://overwolf.github.io/topics/integrations/login-with-overwolf
    """

    OW_URL = "https://accounts.overwolf.com/oauth2"

    # Overwrite values from BaseAuth
    name = "overwolf"
    # supports_inactive_user = False  # Django auth
    # EXTRA_DATA = None
    # GET_ALL_EXTRA_DATA = False
    # REQUIRES_EMAIL_VALIDATION = False
    # SEND_USER_AGENT = False
    # SSL_PROTOCOL = None

    # Overwrite values from OAuthAuth
    ACCESS_TOKEN_METHOD = "POST"
    ACCESS_TOKEN_URL = f"{OW_URL}/token"
    AUTHORIZATION_URL = f"{OW_URL}/auth"
    # DEFAULT_SCOPE = None
    ID_KEY: Literal["username"] = "username"  # Default was "id"
    # REVOKE_TOKEN_METHOD = "POST"
    # REVOKE_TOKEN_URL = None
    # SCOPE_PARAMETER_NAME = "scope"
    # SCOPE_SEPARATOR = " "

    # Overwrite values from BaseOAuth2
    REDIRECT_STATE = False  # Disable state validation
    # REFRESH_TOKEN_METHOD = "POST"
    # REFRESH_TOKEN_URL = None
    # RESPONSE_TYPE = "code"
    STATE_PARAMETER = False  # Disable state validation

    def extra_data(
        self,
        user: Any,
        uid: Any,
        response: Response,
        details: UserDetails = None,
        *args,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Override implementation from BaseOAuth2.

        Augment the info stored in "extra_data" database field with info
        from the JWT. The JWT itself is also stored, but not needing to
        decode the token everywhere the info is used makes sense.
        """
        data = super().extra_data(user, uid, response, details=details, *args, **kwargs)

        jwt_data = self._decode_response_jwt(response)
        data["email_verified"] = jwt_data.get("email_verified")
        data["nickname"] = jwt_data.get("nickname")
        data["picture"] = jwt_data.get("picture")
        data["preferred_username"] = jwt_data.get("preferred_username")

        return data

    def get_user_details(self, response: Response) -> UserDetails:
        """
        Override implementation from BaseAuth.

        Returned "know internal struct" shouldn't be changed.
        """
        data = self._decode_response_jwt(response)

        try:
            username = data["sub"]
        except KeyError:
            raise AuthException("JWT contained no username (sub)")

        return {
            "username": username,
            "email": data.get("email", ""),
            "fullname": "",
            "first_name": "",
            "last_name": "",
        }

    def get_user_id(self, details: UserDetails, response: Response) -> str:
        """
        Override implementation from BaseAuth.

        By default the value is read from response, but it's JWT
        encoded, so read the value from details instead.
        """
        return details[self.ID_KEY]

    def _decode_response_jwt(self, response: Response) -> Dict[str, Any]:
        """
        Verify and decode JWT with Overwolf's public key.
        """
        token: Optional[str] = response.get("id_token")

        if token is None:
            raise AuthException("No id_token in auth response")

        return decode_jwt(token)
