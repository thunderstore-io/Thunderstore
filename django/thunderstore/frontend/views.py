from django.conf import settings
from django.shortcuts import render
from django.utils.decorators import classonlymethod, method_decorator
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView

from thunderstore.repository.mixins import CommunityMixin


def disable_cache_if_static_request(request, response):
    if request.path.startswith(settings.STATIC_URL):
        response["Cache-Control"] = "no-cache"


class ErrorHandler(View, CommunityMixin):

    # TODO: Lines 41 through 52 were introduced in Django 4.0a1
    # And are needed for the error handler views
    # Grap these here temporarily until we can get the Django update done
    # TS-425
    @classonlymethod
    def as_view(cls, **initkwargs):
        """Main entry point for a request-response process."""
        for key in initkwargs:
            if key in cls.http_method_names:
                raise TypeError(
                    "The method name %s is not accepted as a keyword argument "
                    "to %s()." % (key, cls.__name__)
                )
            if not hasattr(cls, key):
                raise TypeError(
                    "%s() received an invalid keyword %r. as_view "
                    "only accepts arguments that are already "
                    "attributes of the class." % (cls.__name__, key)
                )

        def view(request, *args, **kwargs):
            self = cls(**initkwargs)
            self.setup(request, *args, **kwargs)
            if not hasattr(self, "request"):
                raise AttributeError(
                    "%s instance has no 'request' attribute. Did you override "
                    "setup() and forget to call super()?" % cls.__name__
                )
            return self.dispatch(request, *args, **kwargs)

        view.view_class = cls
        view.view_initkwargs = initkwargs

        # __name__ and __qualname__ are intentionally left unchanged as
        # view_class should be used to robustly determine the name of the view
        # instead.
        view.__doc__ = cls.__doc__
        view.__module__ = cls.__module__
        view.__annotations__ = cls.dispatch.__annotations__
        # Copy possible attributes set by decorators, e.g. @csrf_exempt, from
        # the dispatch method.
        view.__dict__.update(cls.dispatch.__dict__)

        return view

    def get_locals(self):
        locals = {}
        locals["community_identifier"] = self.community_identifier
        locals["community"] = self.community
        locals["community_site"] = self.community_site
        locals["use_old_urls"] = self.use_old_urls
        return locals


class Handler404(ErrorHandler):
    def dispatch(self, request, *args, **kwargs):
        response = render(request, "errors/404.html", self.get_locals(), status=404)
        disable_cache_if_static_request(request, response)
        return response


class Handler500(ErrorHandler):
    def dispatch(self, request, *args, **kwargs):
        response = render(request, "errors/500.html", self.get_locals(), status=500)
        disable_cache_if_static_request(request, response)
        return response


def ads_txt_view(request):
    return render(request, "ads.txt", locals())


def robots_txt_view(request):
    return render(request, "robots.txt", locals())


@method_decorator(ensure_csrf_cookie, name="dispatch")
class MarkdownPreviewView(CommunityMixin, TemplateView):
    template_name = "frontend/markdown_preview.html"


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ManifestV1ValidatorView(CommunityMixin, TemplateView):
    template_name = "frontend/manifest_v1_validator.html"
