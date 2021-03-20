from typing import Any

import pytest
from django.core.exceptions import ValidationError
from django.test import RequestFactory

from thunderstore.core.utils import check_validity, make_full_url


def test_check_validity_fail() -> None:
    def fail_fn():
        raise ValidationError("test")

    assert check_validity(lambda: fail_fn()) is False


def test_check_validity_success() -> None:
    def success_fn():
        pass

    assert check_validity(lambda: success_fn()) is True


@pytest.mark.parametrize("scheme", ("http://", "https://"))
def test_make_full_url(scheme: str, rf: RequestFactory, settings: Any) -> None:
    settings.PROTOCOL = scheme
    request = rf.get("")
    expected = f"{scheme}testserver/test/path/"
    assert make_full_url(request, "/test/path/") == expected
    assert make_full_url(None, "/test/path/") == "/test/path/"
