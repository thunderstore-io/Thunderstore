from typing import Any, Optional

import pytest
from django.core.exceptions import ValidationError
from django.test import RequestFactory, override_settings

from thunderstore.core.utils import (
    capture_exception,
    check_validity,
    extend_update_fields_if_present,
    make_full_url,
    replace_cdn,
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
def test_make_full_url(scheme: str, rf: RequestFactory, settings: Any) -> None:
    settings.PROTOCOL = scheme
    request = rf.get("")
    expected = f"{scheme}testserver/test/path/"
    assert make_full_url(request, "/test/path/") == expected
    assert make_full_url(None, "/test/path/") == "/test/path/"


@pytest.mark.parametrize(
    ("filename", "expected"),
    (
        (None, None),
        ("", ""),
        ("/", ""),
        ("testfile😁😁", "testfile"),
        ('testfile¤%=///\\\\.!"(¤)=!"', "testfile."),
        (
            "abcdefghijklmnopqrstuvxyzABCDEFGHIJKLMNOPQRSTUVXYZ1234567890._-",
            "abcdefghijklmnopqrstuvxyzABCDEFGHIJKLMNOPQRSTUVXYZ1234567890._-",
        ),
    ),
)
def test_sanitize_filename(filename: Optional[str], expected: Optional[str]) -> None:
    assert sanitize_filename(filename) == expected


@pytest.mark.parametrize(
    ("filepath", "expected"),
    (
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
    ),
)
def test_sanitize_filepath(filepath: Optional[str], expected: Optional[str]) -> None:
    assert sanitize_filepath(filepath) == expected


@pytest.mark.parametrize(
    ("filepath", "should_fail"),
    (
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
    ),
)
def test_validate_filepath_prefix(filepath: Optional[str], should_fail: bool) -> None:
    if should_fail:
        with pytest.raises(ValidationError, match="Invalid filepath prefix"):
            validate_filepath_prefix(filepath)
    else:
        assert validate_filepath_prefix(filepath) == filepath


def test_capture_exception_always_raise(settings: Any):
    settings.ALWAYS_RAISE_EXCEPTIONS = False
    capture_exception(Exception("test"))
    settings.ALWAYS_RAISE_EXCEPTIONS = True
    with pytest.raises(Exception, match="test"):
        capture_exception(Exception("test"))


@pytest.mark.parametrize(
    ("url", "preferred", "expected"),
    (
        (
            "https://gcdn.thunderstore.io/healthz",
            None,
            "https://gcdn.thunderstore.io/healthz",
        ),
        (
            "https://gcdn.thunderstore.io/healthz",
            "",
            "https://gcdn.thunderstore.io/healthz",
        ),
        (
            "https://gcdn.thunderstore.io/healthz",
            "disallowed.thunderstore.io",
            "https://gcdn.thunderstore.io/healthz",
        ),
        (
            "https://gcdn.thunderstore.io/healthz",
            "gcdn.thunderstore.io",
            "https://gcdn.thunderstore.io/healthz",
        ),
        (
            "https://gcdn.thunderstore.io/healthz",
            "hcdn-1.hcdn.thunderstore.io",
            "https://hcdn-1.hcdn.thunderstore.io/healthz",
        ),
        (
            "https://gcdn.thunderstore.io",
            "hcdn-1.hcdn.thunderstore.io",
            "https://hcdn-1.hcdn.thunderstore.io",
        ),
        (
            "https://hcdn-1.hcdn.thunderstore.io/healthz",
            "gcdn.thunderstore.io",
            "https://gcdn.thunderstore.io/healthz",
        ),
        (
            "http://localhost.thunderstore/healthz",
            "hcdn-1.hcdn.thunderstore.io",
            "http://hcdn-1.hcdn.thunderstore.io/healthz",
        ),
        (
            "http://localhost:9000/healthz",
            "hcdn-1.hcdn.thunderstore.io",
            "http://hcdn-1.hcdn.thunderstore.io/healthz",
        ),
    ),
)
@override_settings(ALLOWED_CDNS=["gcdn.thunderstore.io", "hcdn-1.hcdn.thunderstore.io"])
def test_replace_cdn(
    url: str,
    preferred: Optional[str],
    expected: str,
) -> None:
    assert replace_cdn(url, preferred) == expected


@pytest.mark.parametrize(
    "url",
    (
        "",
        "/",
        "/relative/path",
        "//thunderstore.io/protocol/relative/path",
    ),
)
def test_replace_cdn__raises_for_relative_urls(url: str) -> None:
    with pytest.raises(
        ValueError,
        match="Absolute URL including protocol required",
    ):
        replace_cdn(url, "irrelevant")


def test_extend_update_fields_if_present__no_update_fields_key() -> None:
    original = {"some": "value"}
    result = extend_update_fields_if_present(original, "new_field")
    assert result is not original
    # Should not add update_fields key when it's not present in original
    assert "update_fields" not in result
    # Original dict remains unchanged
    assert original == {"some": "value"}


def test_extend_update_fields_if_present__update_fields_none() -> None:
    original = {"update_fields": None, "other": 1}
    result = extend_update_fields_if_present(original, "x")
    # Copy returned
    assert result is not original
    # When update_fields is None, it should be left as-is
    assert result["update_fields"] is None
    assert result["other"] == 1
    # Original remains unmodified
    assert original["update_fields"] is None


def test_extend_update_fields_if_present__extends_and_deduplicates() -> None:
    original = {"update_fields": ["a", "b"]}
    result = extend_update_fields_if_present(original, "b", "c")
    # Should return a set with union of existing and new fields
    assert isinstance(result["update_fields"], set)
    assert result["update_fields"] == {"a", "b", "c"}
    # Original should not be mutated
    assert original["update_fields"] == ["a", "b"]


def test_extend_update_fields_if_present__accepts_tuple_and_empty_new_fields() -> None:
    original = {"update_fields": ("x",)}
    result = extend_update_fields_if_present(original)
    assert result["update_fields"] == {"x"}
