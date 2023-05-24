from functools import lru_cache
from typing import Callable, List

from django.http import HttpRequest, HttpResponse
from django.utils import timezone

from thunderstore.account.models import UserFlag


class UserFlagsHttpRequest(HttpRequest):
    get_user_flags: Callable[[], List[str]]


class UserFlagsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: UserFlagsHttpRequest) -> HttpResponse:
        user = getattr(request, "user", None)

        @lru_cache(maxsize=1)
        def get_user_flags() -> List[str]:
            return UserFlag.get_active_flags_on_user(user, timezone.now())

        request.get_user_flags = get_user_flags
        return self.get_response(request)
