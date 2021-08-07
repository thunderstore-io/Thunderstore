from typing import Any, Optional

from django.core.exceptions import ValidationError as DjangoValidationError
from drf_yasg.openapi import Response
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.serializers import as_serializer_error
from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc: Exception, context: Any) -> Optional[Response]:
    if isinstance(exc, DjangoValidationError):
        exc = DRFValidationError(detail=as_serializer_error(exc))
    response = drf_exception_handler(exc, context)
    if response:
        return response
    return None
