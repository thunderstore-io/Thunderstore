from typing import Any, Optional

import pytest
from django.core.exceptions import ValidationError
from django.test import RequestFactory

from thunderstore.community.models.community_site import CommunitySite
from thunderstore.core.utils import (
    build_url_from_request_object,
    build_url_from_site_object,
    check_validity,
    enforce_url_protocol,
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


@pytest.mark.parametrize("scheme", ("http://", "https://"))
def test_build_url_from_request_object(scheme: str, rf: RequestFactory, settings: Any):
    settings.PROTOCOL = scheme
    request = rf.get("")
    expected = f"{scheme}testserver/test/path/"
    assert build_url_from_request_object("/test/path/", request) == expected
    assert build_url_from_request_object("/test/path/", None) == "/test/path/"


@pytest.mark.django_db
@pytest.mark.parametrize("scheme", ("http://", "https://"))
def test_build_url_from_site_object(
    scheme: str, community_site: CommunitySite, settings: Any
):
    settings.PROTOCOL = scheme
    assert (
        build_url_from_site_object("/test/path", community_site.site)
        == f"{settings.PROTOCOL}{community_site.site.domain}/test/path"
    )


def test_enforce_url_protocol(settings: Any) -> None:
    settings.PROTOCOL = "https://"
    assert enforce_url_protocol("testserver/test/path/") == "testserver/test/path/"
    assert (
        enforce_url_protocol("http://testserver/test/path/")
        == "https://testserver/test/path/"
    )
