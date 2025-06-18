from typing import Any, Dict

from django.conf import settings
from django.shortcuts import render
from django.utils.cache import patch_cache_control
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import RedirectView, TemplateView

from thunderstore.frontend.services.thumbnail import get_or_create_thumbnail
from thunderstore.plugins.registry import plugin_registry


def disable_cache_if_static_request(request, response):
    if request.path.startswith(settings.STATIC_URL):
        response["Cache-Control"] = "no-cache"


def handle404(request, exception=None):
    response = render(request, "errors/404.html", locals(), status=404)
    disable_cache_if_static_request(request, response)
    return response


def handle500(request):
    response = render(request, "errors/500.html", locals(), status=500)
    disable_cache_if_static_request(request, response)
    return response


def ads_txt_view(request):
    return render(request, "ads.txt", locals())


def robots_txt_view(request):
    return render(request, "robots.txt", locals())


@method_decorator(ensure_csrf_cookie, name="dispatch")
class MarkdownPreviewView(TemplateView):
    template_name = "frontend/markdown_preview.html"


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ManifestV1ValidatorView(TemplateView):
    template_name = "frontend/manifest_v1_validator.html"


class SettingsViewMixin:
    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["setting_links"] = plugin_registry.get_settings_links()
        return context


class ThumbnailRedirectView(RedirectView):
    fallback_url = ""

    def get_redirect_url(self, *args, **kwargs):
        asset_path = self.kwargs.get("path")

        try:
            width = int(self.request.GET.get("width", 0))
            height = int(self.request.GET.get("height", 0))
        except (ValueError, TypeError):
            width, height = 0, 0

        if asset_path and width > 0 and height > 0:
            url = get_or_create_thumbnail(asset_path, width, height)
            if url:
                return url

        return self.fallback_url

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        patch_cache_control(response, max_age=86400, public=True)  # 24 hours
        return response
