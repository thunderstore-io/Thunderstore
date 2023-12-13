from django.conf import settings
from drf_yasg.utils import swagger_auto_schema, unset


def conditional_swagger_auto_schema(*args, **kwargs):
    def decorator(f):
        if settings.SHOW_CYBERSTORM_API_DOCS:
            return swagger_auto_schema(*args, auto_schema=unset, **kwargs)(f)
        return swagger_auto_schema(*args, auto_schema=None, **kwargs)(f)

    return decorator


class CyberstormAutoSchemaMixin:  # pragma: no cover
    """
    Control Cyberstorm API endpoint visibility in Swagger docs.

    Use SHOW_CYBERSTORM_API_DOCS env variable to control whether the
    endpoints are included in the API documentation or not.
    """

    @conditional_swagger_auto_schema(tags=["cyberstorm"])
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)

    @conditional_swagger_auto_schema(tags=["cyberstorm"])
    def post(self, *args, **kwargs):
        return super().get(*args, **kwargs)
