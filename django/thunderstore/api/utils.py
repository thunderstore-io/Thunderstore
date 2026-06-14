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

    1. Caching: Applies 'public' Cache-Control headers to the response. The
       response is cacheable by both browsers (max-age) and shared/CDN caches
       (s-maxage), with a stale-while-revalidate window so the CDN can serve
       slightly-stale data while it refreshes in the background. These mirror the
       cyberstorm-remix page caching defaults so the API and the pages it backs
       cache consistently.
    2. Security: Explicitly clears 'authentication_classes' and 'permission_classes'
       to override global DRF settings in settings.py. This ensures the endpoint is strictly
       anonymous and prevents 'request.user' from being populated, which
       mitigates the risk of caching user-specific data — and, in turn, makes the
       shared/CDN (s-maxage) caching below safe (no per-user output to cross-serve).
    """

    authentication_classes = []
    permission_classes = []

    cache_max_age = 60  # browser max-age, seconds
    # Shared/CDN freshness lifetime (s-maxage). Set to None to keep a response
    # browser-only (no shared caching).
    cache_shared_max_age = 300  # seconds
    # How long a shared cache may serve stale content while revalidating. Set to
    # None to omit the directive.
    cache_stale_while_revalidate = 600  # seconds
    cache_404s = False

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)

        if response.status_code == 200 or (
            response.status_code == 404 and self.cache_404s
        ):
            directives = {"public": True, "max_age": self.cache_max_age}
            if self.cache_shared_max_age is not None:
                directives["s_maxage"] = self.cache_shared_max_age
            if self.cache_stale_while_revalidate is not None:
                directives["stale_while_revalidate"] = self.cache_stale_while_revalidate
            patch_cache_control(response, **directives)
        return response


class NeverCacheMixin:
    """
    A mixin for endpoints whose responses must never be stored by any cache —
    browser, shared or CDN. Use it for responses that contain secrets/tokens
    (e.g. a freshly minted service-account API token) or that are otherwise
    user-specific or non-idempotent.

    Sets ``Cache-Control: private, no-store``. POST endpoints are already not
    stored by well-behaved shared caches, but making the intent explicit guards
    against intermediary caches and future changes to the view (e.g. adding a
    GET) — see TS QA caching notes.

    Unlike PublicCacheMixin this does NOT touch authentication/permission
    classes; the endpoint keeps its own. Place before the DRF view base classes
    in the inheritance list.
    """

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        patch_cache_control(response, no_store=True, private=True)
        return response
