from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar

import requests
from django.conf import settings
from pydantic import BaseModel


class AuthResponseSchema(BaseModel):
    access_token: str
    expires_in: Optional[int] = None
    refresh_token: Optional[str] = None
    scope: str
    token_type: str


class UserInfoSchema(BaseModel):
    email: str
    extra_data: Dict[str, Any]
    name: str
    uid: str
    username: str


BaseModelSubtype = TypeVar("BaseModelSubtype", bound=BaseModel)


class BaseOauthHelper(ABC):
    token: Optional[str] = None

    @property
    @abstractmethod
    def AUTH_HEADER_KEYWORD(self) -> str:
        """
        Scheme keyword for HTTP Authorization header, e.g. "Bearer".
        """

    @property
    @abstractmethod
    def CLIENT_ID(self) -> str:
        """
        Public identifier for Thunderstore issued by the provider.
        """

    @property
    @abstractmethod
    def CLIENT_SECRET(self) -> str:
        """
        Private authentication token, issued by the provider.
        """

    @property
    @abstractmethod
    def OAUTH_URL(self) -> str:
        """
        URL for exchanging an authorization code for an access token.
        """

    def __init__(self, code: str, redirect_uri: str) -> None:
        self.code = code
        self.redirect_uri = redirect_uri

    def complete_login(self) -> None:
        """
        Fetch access token with the temporary code and configured secret.
        """
        data = {
            "client_id": self.CLIENT_ID,
            "client_secret": self.CLIENT_SECRET,
            "code": self.code,
            "grant_type": "authorization_code",  # Required by Discord
            "redirect_uri": self.redirect_uri,  # Required by Discord
        }
        headers = {"Accept": "application/json"}

        response = requests.post(self.OAUTH_URL, data, headers=headers)
        response_data = AuthResponseSchema.parse_obj(response.json())
        self.token = response_data.access_token

    @abstractmethod
    def get_user_info(self) -> UserInfoSchema:
        """
        Fetch user info from a public API.
        """

    def _raise_for_token(self, token: Optional[str]) -> str:
        """
        Check access token is set before allowing public API calls.
        """
        if token is None:
            raise Exception("No token found. Did you call .complete_login()?")

        return token

    def _fetch_from_api(self, token: str, url: str) -> Dict[str, Any]:
        """
        Use access token to fetch info from provider's public API.
        """
        headers = {"Authorization": f"{self.AUTH_HEADER_KEYWORD} {token}"}
        response = requests.get(url, headers=headers)
        return response.json()


class DiscordOauthHelper(BaseOauthHelper):
    """
    Helper class for Discord's OAuth authentication flow.
    """

    AUTH_HEADER_KEYWORD = "Bearer"
    CLIENT_ID = settings.SOCIAL_AUTH_DISCORD_KEY
    CLIENT_SECRET = settings.SOCIAL_AUTH_DISCORD_SECRET
    OAUTH_URL = "https://discord.com/api/v8/oauth2/token"

    def get_user_info(self) -> UserInfoSchema:
        """
        Fetch user info from Discord's API using the access token.

        """
        token = self._raise_for_token(self.token)
        url = "https://discord.com/api/v8/users/@me"

        class PartialResponseSchema(BaseModel):
            """
            For full schema see
            https://github.com/discord/discord-api-docs/blob/main/docs/resources/User.md
            """

            email: str
            id: str
            username: str

        response_json = self._fetch_from_api(token, url)
        data = PartialResponseSchema.parse_obj(response_json)

        return UserInfoSchema.parse_obj(
            {
                "email": data.email,
                "extra_data": response_json,
                "name": "",
                "uid": data.id,
                "username": data.username,
            }
        )


class GitHubOauthHelper(BaseOauthHelper):
    """
    Helper class for GitHub's OAuth authentication flow.
    """

    AUTH_HEADER_KEYWORD = "token"
    CLIENT_ID = settings.SOCIAL_AUTH_GITHUB_KEY
    CLIENT_SECRET = settings.SOCIAL_AUTH_GITHUB_SECRET
    OAUTH_URL = "https://github.com/login/oauth/access_token"

    def get_user_email(self) -> str:
        """
        Fetch user's email from GitHub's API using the access token.

        If user has chosen to make their email hidden, it won't be
        included in the user's basic information, but it can be fetched
        with a separate request.
        """
        token = self._raise_for_token(self.token)
        url = "https://api.github.com/user/emails"

        class PartialEmail(BaseModel):
            """
            For full schema see https://docs.github.com/en/rest/users/emails
            """

            email: str
            primary: bool
            verified: bool

        class EmailList(BaseModel):
            __root__: List[PartialEmail]

            def __iter__(self):
                return iter(self.__root__)

        response_json = self._fetch_from_api(token, url)
        emails = EmailList.parse_obj(response_json)
        primary = next((email for email in emails if email.primary), None)

        if primary is None or not primary.verified:
            raise Exception("User has no email available")

        return primary.email

    def get_user_info(self) -> UserInfoSchema:
        """
        Fetch user info from GitHub's API using the access token.
        """
        token = self._raise_for_token(self.token)
        url = "https://api.github.com/user"

        class PartialResponseSchema(BaseModel):
            """
            For full schema see https://docs.github.com/en/rest/users/users
            """

            email: Optional[str] = None
            id: str
            login: str
            name: str

        response_json = self._fetch_from_api(token, url)
        data = PartialResponseSchema.parse_obj(response_json)

        return UserInfoSchema.parse_obj(
            {
                "email": data.email or self.get_user_email(),
                "extra_data": response_json,
                "name": data.name,
                "uid": data.id,
                "username": data.login,
            }
        )


def get_helper(provider: str) -> Optional[Type[BaseOauthHelper]]:
    return {
        "discord": DiscordOauthHelper,
        "github": GitHubOauthHelper,
    }.get(provider.lower())
