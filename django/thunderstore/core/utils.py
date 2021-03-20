import os
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


class CommunitySiteSerializerContext:
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["community_site"] = self.request.community_site
        return context


def capture_exception(exception: Exception) -> None:
    """Raises exception when running tests or NO_SILENT_FAIL."""
    testing = "PYTEST_CURRENT_TEST" in os.environ
    if testing or not settings.SILENT_FAIL:
        raise exception
    else:
        capture_sentry_exception(exception)


def check_validity(fn: Callable[[], None]) -> bool:
    try:
        fn()
        return True
    except ValidationError:
        return False


def make_full_url(request: Optional[HttpRequest], path: str):
    """Build an URL relative to a request using the proper request scheme"""
    url = path
    if request:
        url = request.build_absolute_uri(url)
    if settings.PROTOCOL == "https://" and url.startswith("http://"):
        url = f"https://{url[7:]}"
    return url
