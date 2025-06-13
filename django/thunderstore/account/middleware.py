from functools import lru_cache
from typing import Callable, List

from django.http import HttpRequest, HttpResponse
from django.utils import timezone

from thunderstore.account.models import UserFlag
from thunderstore.account.models.user_meta import UserMeta
from thunderstore.repository.views.package._utils import get_moderated_communities


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


class UserMetaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)

        request.user_can_moderate_any_community = False
        request.user_moderated_communities = []

        if user and user.is_authenticated:
            try:
                user_meta = UserMeta.objects.get(user=user)
                if user_meta and user_meta.can_moderate_any_community:
                    request.user_can_moderate_any_community = True
                    request.user_moderated_communities = get_moderated_communities(user)
            except UserMeta.DoesNotExist:
                request.user_moderated_communities = get_moderated_communities(user)
                can_moderate_any_community = bool(request.user_moderated_communities)
                request.user_can_moderate_any_community = can_moderate_any_community
                UserMeta.objects.create(
                    user=user, can_moderate_any_community=can_moderate_any_community
                )

        return self.get_response(request)
