from typing import Any, Optional

from django.core.exceptions import ValidationError as DjangoValidationError
from drf_yasg.openapi import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.serializers import as_serializer_error
from rest_framework.views import exception_handler as drf_exception_handler

from thunderstore.core.exceptions import PermissionValidationError


def django_validation_to_drf_error(error: DjangoValidationError) -> DRFValidationError:
    return DRFValidationError(detail=as_serializer_error(error))


def serialize_validation_error(error: DjangoValidationError):
    return django_validation_to_drf_error(error).detail


def exception_handler(exc: Exception, context: Any) -> Optional[Response]:
    if isinstance(exc, PermissionValidationError):
        if exc.is_public:
            exc = PermissionDenied(detail=as_serializer_error(exc))
        else:
            exc = PermissionDenied()

    elif isinstance(exc, DjangoValidationError):
        exc = django_validation_to_drf_error(exc)

    elif isinstance(exc, PermissionError):
        exc = PermissionDenied(detail=exc)

    response = drf_exception_handler(exc, context)
    if response:
        return response
    return None
