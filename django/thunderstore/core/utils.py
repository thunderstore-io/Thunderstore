import re
import urllib.parse
from typing import Any, Callable, Dict, List, Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from sentry_sdk import capture_exception as capture_sentry_exception


class ChoiceEnum(object):
    @classmethod
    def as_choices(cls):
        return [
            (key, value)
            for key, value in vars(cls).items()
            if not key.startswith("_")
            and any(
                (
                    isinstance(value, str),
                    isinstance(value, int),
                    isinstance(value, float),
                    isinstance(value, list),
                    isinstance(value, dict),
                )
            )
        ]

    @classmethod
    def options(cls):
        return [
            value
            for key, value in vars(cls).items()
            if not key.startswith("_")
            and any(
                (
                    isinstance(value, str),
                    isinstance(value, int),
                    isinstance(value, float),
                    isinstance(value, list),
                    isinstance(value, dict),
                )
            )
        ]


def ensure_fields_editable_on_creation(readonly_fields, obj, editable_fields):
    if obj:
        return readonly_fields
    else:
        # Creating the object so make restaurant editable
        return list(x for x in readonly_fields if x not in editable_fields)


def check_validity(fn: Callable[[], None]) -> bool:
    try:
        fn()
        return True
    except ValidationError:
        return False


def capture_exception(error=None, *args, **kwargs):
    if settings.ALWAYS_RAISE_EXCEPTIONS:
        raise error
    capture_sentry_exception(error, *args, **kwargs)


class ExceptionLogger:
    def __init__(self, continue_on_error: bool):
        self.continue_on_error = continue_on_error

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            capture_exception(exc_val)
            if self.continue_on_error:
                return True


def make_full_url(request: Optional[HttpRequest], path: str):
    """Build an URL relative to a request using the proper request scheme"""
    url = path
    if request:
        url = request.build_absolute_uri(url)
    if settings.PROTOCOL == "https://" and url.startswith("http://"):
        url = f"https://{url[7:]}"
    return url


FILENAME_SANITIZER_REGEX = re.compile(r"[^a-zA-Z0-9\_\-\.]+")


def sanitize_filename(filename: Optional[str]) -> Optional[str]:
    if filename is None:
        return None
    return re.sub(FILENAME_SANITIZER_REGEX, "", filename)


def sanitize_filepath(filepath: Optional[str]) -> Optional[str]:
    if filepath is None:
        return None
    return "/".join(
        [
            sanitize_filename(x)
            for x in filepath.replace("\\", "/").split("/")
            if sanitize_filename(x.replace(".", ""))
        ]
    )


def extend_update_fields_if_present(
    original_kwargs: Dict[str, Any], *new_fields: str
) -> Dict[str, Any]:
    """Returns a copy of original_kwargs with the update_fields field updated"""
    result = {**original_kwargs}
    if (upfields := original_kwargs.get("update_fields")) is not None:
        result["update_fields"] = {*upfields, *new_fields}
    return result


def validate_filepath_prefix(filepath: Optional[str]) -> Optional[str]:
    stripped = sanitize_filepath(filepath)
    if stripped != filepath:
        raise ValidationError(
            f"Invalid filepath prefix: {filepath}, should be: {stripped}"
        )
    return stripped


def replace_cdn(absolute_url: str, domain: Optional[str]):
    # The implementation would change any relative URL to a
    # "protocol-relative URL", which may or may not be what some future
    # users would expect. Better ~safe~ raise than sorry.
    if not absolute_url.lower().startswith("http"):
        raise ValueError("Absolute URL including protocol required")

    if domain and domain in settings.ALLOWED_CDNS:
        parsed = urllib.parse.urlparse(absolute_url)
        parsed = parsed._replace(netloc=domain)
        return parsed.geturl()

    return absolute_url
