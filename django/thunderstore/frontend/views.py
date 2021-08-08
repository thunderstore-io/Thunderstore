from django.shortcuts import render
from django.views.generic import TemplateView


def handle404(request, exception):
    return render(request, "errors/404.html", locals())


def handle500(request):
    return render(request, "errors/500.html", locals())


def ads_txt_view(request):
    return render(request, "ads.txt", locals())


def robots_txt_view(request):
    return render(request, "robots.txt", locals())


class MarkdownPreviewView(TemplateView):
    template_name = "frontend/markdown_preview.html"


class ManifestV1ValidatorView(TemplateView):
    template_name = "frontend/manifest_v1_validator.html"
