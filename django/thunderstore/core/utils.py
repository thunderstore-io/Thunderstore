import re
from typing import Callable, Optional

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


def capture_exception(*args, **kwargs):
    capture_sentry_exception(*args, **kwargs)


def make_full_url(request: Optional[HttpRequest], path: Optional[str] = None):
    """Build an URL relative to a request using the proper request scheme"""
    url = path
    if request:
        url = request.build_absolute_uri(url)
        query_string = request.META.get("QUERY_STRING", "")
        if query_string:
            url = "%s?%s" % (url, query_string)
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


def validate_filepath_prefix(filepath: Optional[str]) -> Optional[str]:
    stripped = sanitize_filepath(filepath)
    if stripped != filepath:
        raise ValidationError(
            f"Invalid filepath prefix: {filepath}, should be: {stripped}"
        )
    return stripped
