from django.conf import settings
from drf_yasg.utils import swagger_auto_schema, unset


def conditional_swagger_auto_schema(*args, **kwargs):
    def decorator(f):
        if settings.SHOW_CYBERSTORM_API_DOCS:
            return swagger_auto_schema(*args, auto_schema=unset, **kwargs)(f)
        return swagger_auto_schema(*args, auto_schema=None, **kwargs)(f)

    return decorator
