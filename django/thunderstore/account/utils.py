from typing import List

from thunderstore.account.middleware import UserFlagsHttpRequest


def get_request_user_flags(request: UserFlagsHttpRequest) -> List[str]:
    get_flags = getattr(request, "get_user_flags", lambda: [])
    return get_flags()
