from typing import Any, Optional

import pytest
from django.core.exceptions import ValidationError
from django.test import RequestFactory

from thunderstore.core.utils import (
    check_validity,
    make_full_url,
    sanitize_filename,
    sanitize_filepath,
    validate_filepath_prefix,
)


def test_check_validity_fail() -> None:
    def fail_fn():
        raise ValidationError("test")

    assert check_validity(lambda: fail_fn()) is False


def test_check_validity_success() -> None:
    def success_fn():
        pass

    assert check_validity(lambda: success_fn()) is True


@pytest.mark.parametrize("scheme", ("http://", "https://"))
@pytest.mark.parametrize("query_string", ("test=string&isa=teststring", ""))
def test_make_full_url(
    scheme: str, query_string: str, rf: RequestFactory, settings: Any
) -> None:
    settings.PROTOCOL = scheme
    request = rf.get("")
    expected = f"{scheme}testserver/test/path/"
    assert make_full_url(request, "/test/path/") == expected
    request.META.update({"QUERY_STRING": query_string})
    if query_string:
        assert (
            make_full_url(request, "/test/path/", transfer_query_string=True)
            == expected + "?" + query_string
        )
    else:
        assert (
            make_full_url(request, "/test/path/", transfer_query_string=True)
            == expected
        )
    assert make_full_url(None, "/test/path/") == "/test/path/"


@pytest.mark.parametrize(
    ["filename", "expected"],
    [
        (None, None),
        ("", ""),
        ("/", ""),
        ("testfile😁😁", "testfile"),
        ('testfile¤%=///\\\\.!"(¤)=!"', "testfile."),
        (
            "abcdefghijklmnopqrstuvxyzABCDEFGHIJKLMNOPQRSTUVXYZ1234567890._-",
            "abcdefghijklmnopqrstuvxyzABCDEFGHIJKLMNOPQRSTUVXYZ1234567890._-",
        ),
    ],
)
def test_sanitize_filename(filename: Optional[str], expected: Optional[str]) -> None:
    assert sanitize_filename(filename) == expected


@pytest.mark.parametrize(
    ["filepath", "expected"],
    [
        (None, None),
        ("", ""),
        ("test/dir/testfile", "test/dir/testfile"),
        ("test/dir//testfile", "test/dir/testfile"),
        ("test/dir/////testfile", "test/dir/testfile"),
        ("test///dir/////testfile", "test/dir/testfile"),
        ("test/././dir//.///testfile", "test/dir/testfile"),
        ("test.../.././/dir////testfile", "test.../dir/testfile"),
        ("test.../.././/dir////testfile😁😁", "test.../dir/testfile"),
        ('test.../.././/dir////testfile!"¤)=(', "test.../dir/testfile"),
        ("test/dir/testfile/", "test/dir/testfile"),
        ("test/dir/testfile///", "test/dir/testfile"),
    ],
)
def test_sanitize_filepath(filepath: Optional[str], expected: Optional[str]) -> None:
    assert sanitize_filepath(filepath) == expected


@pytest.mark.parametrize(
    ["filepath", "should_fail"],
    [
        (None, False),
        ("", False),
        ("test", False),
        ("test.", False),
        ("test./path.", False),
        ("test/dir/testfile", False),
        ("test/dir//testfile", True),
        ("test/dir/////testfile", True),
        ("test///dir/////testfile", True),
        ("test/././dir//.///testfile", True),
        ("test.../.././/dir////testfile", True),
        ("test.../.././/dir////testfile😁😁", True),
        ('test.../.././/dir////testfile!"¤)=(', True),
        ("test/dir/testfile/", True),
        ("test/dir/testfile///", True),
    ],
)
def test_validate_filepath_prefix(filepath: Optional[str], should_fail: bool) -> None:
    if should_fail:
        with pytest.raises(ValidationError, match="Invalid filepath prefix"):
            validate_filepath_prefix(filepath)
    else:
        assert validate_filepath_prefix(filepath) == filepath
