from unittest.mock import MagicMock

from django.test import RequestFactory

from thunderstore.account.utils import get_request_user_flags


def test_utils_get_request_user_flags(rf: RequestFactory):
    request = rf.get("/")
    request.get_user_flags = MagicMock(return_value=["test"])
    result = get_request_user_flags(request)
    request.get_user_flags.assert_called_once()
    assert result == ["test"]
