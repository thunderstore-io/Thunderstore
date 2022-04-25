from django.conf import settings
from django.shortcuts import render
from django.views.generic import TemplateView

from thunderstore.repository.mixins import CommunityMixin


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


class MarkdownPreviewView(CommunityMixin, TemplateView):
    template_name = "frontend/markdown_preview.html"


class ManifestV1ValidatorView(CommunityMixin, TemplateView):
    template_name = "frontend/manifest_v1_validator.html"
