from django.conf import settings
from django.utils.cache import patch_cache_control
from drf_yasg.utils import swagger_auto_schema, unset  # type: ignore


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


class PublicCacheMixin:
    """
    A mixin for caching public API endpoints.

    IMPORTANT: Must be before generic DRF view base classes in the inheritance list.

    Example:
        class ProductListView(PublicCacheMixin, ListAPIView):

    1. Caching: Applies 'public' Cache-Control headers to the response.
    2. Security: Explicitly clears 'authentication_classes' and 'permission_classes'
       to override global DRF settings in settings.py. This ensures the endpoint is strictly
       anonymous and prevents 'request.user' from being populated, which
       mitigates the risk of caching user-specific data.
    """

    authentication_classes = []
    permission_classes = []

    cache_max_age = 60  # seconds
    cache_404s = False

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)

        if response.status_code == 200 or (
            response.status_code == 404 and self.cache_404s
        ):
            patch_cache_control(response, public=True, max_age=self.cache_max_age)
        return response
