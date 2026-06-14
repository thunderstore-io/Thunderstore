from django.http import HttpResponse

from thunderstore.api.utils import NeverCacheMixin, PublicCacheMixin


def parse_cache_control(response):
    """Parse a response's Cache-Control header into a {directive: value|True} dict."""
    raw = response.get("Cache-Control", "")
    directives = {}
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            key, value = part.split("=", 1)
            directives[key.strip().lower()] = value.strip()
        else:
            directives[part.lower()] = True
    return directives


class _Base:
    """Minimal stand-in for a DRF view base that just returns the response."""

    def finalize_response(self, request, response, *args, **kwargs):
        return response


class _PublicView(PublicCacheMixin, _Base):
    pass


class _NeverCacheView(NeverCacheMixin, _Base):
    pass


def test_public_cache_mixin_emits_shared_cache_directives():
    response = _PublicView().finalize_response(None, HttpResponse(status=200))
    directives = parse_cache_control(response)

    # Browser-cacheable AND shared/CDN-cacheable (s-maxage), with a SWR window.
    assert directives.get("public") is True
    assert directives.get("max-age") == "60"
    assert directives.get("s-maxage") == "300"
    assert directives.get("stale-while-revalidate") == "600"


def test_public_cache_mixin_does_not_cache_error_responses():
    response = _PublicView().finalize_response(None, HttpResponse(status=500))
    assert response.get("Cache-Control", "") == ""


def test_public_cache_mixin_can_stay_browser_only():
    view = _PublicView()
    view.cache_shared_max_age = None
    view.cache_stale_while_revalidate = None

    response = view.finalize_response(None, HttpResponse(status=200))
    directives = parse_cache_control(response)

    assert directives.get("public") is True
    assert directives.get("max-age") == "60"
    assert "s-maxage" not in directives
    assert "stale-while-revalidate" not in directives


def test_never_cache_mixin_forbids_storing_the_response():
    response = _NeverCacheView().finalize_response(None, HttpResponse(status=200))
    directives = parse_cache_control(response)

    assert "no-store" in directives
    assert "private" in directives
