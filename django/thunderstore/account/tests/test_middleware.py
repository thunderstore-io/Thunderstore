from unittest.mock import MagicMock

import pytest
from django.test import RequestFactory

from thunderstore.account.middleware import UserFlagsMiddleware
from thunderstore.account.models import UserFlag


def test_middleware_get_user_flags_is_set_to_request(rf: RequestFactory):
    get_response = MagicMock()
    request = rf.get("/")

    middleware = UserFlagsMiddleware(get_response)

    assert not hasattr(request, "get_user_flags")
    response = middleware(request)
    assert hasattr(request, "get_user_flags")
    assert callable(getattr(request, "get_user_flags"))

    get_response.assert_called_once()
    assert response == get_response.return_value


@pytest.mark.django_db
def test_middleware_get_user_flags_is_cached(mocker, rf: RequestFactory):
    get_response = MagicMock()
    request = rf.get("/")

    middleware = UserFlagsMiddleware(get_response)
    middleware(request)

    assert hasattr(request, "get_user_flags")
    spy = mocker.spy(UserFlag, "get_active_flags_on_user")
    assert request.get_user_flags() == []
    assert spy.call_count == 1
    [request.get_user_flags() for _ in range(3)]
    assert spy.call_count == 1
