from functools import lru_cache

from django.http import HttpResponse
from django.shortcuts import render
from social_core.exceptions import AuthAlreadyAssociated, AuthCanceled, AuthFailed

from thunderstore.frontend.models import DynamicHTML


# TODO: Move to it's own auth module if more auth related things are needed
class SocialAuthExceptionHandlerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        template = None

        if isinstance(exception, AuthAlreadyAssociated):
            template = "errors/auth_already_associated.html"
        elif isinstance(exception, AuthFailed):
            template = "errors/auth_failed.html"
        elif isinstance(exception, AuthCanceled):
            template = "errors/auth_canceled.html"

        if template:
            return HttpResponse(render(request, template))
        return None


class DynamicHTMLMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        community = getattr(request, "community", None)
        user_flags = (
            request.get_user_flags() if hasattr(request, "get_user_flags") else []
        )

        @lru_cache(maxsize=1)
        def get_dynamic_html():
            entries = DynamicHTML.get_for_community(
                community=community,
                user_flags=user_flags,
                placement=None,
            ).values_list("placement", "content")

            result = {}
            for placement, content in entries:
                if content:
                    result.setdefault(placement, "")
                    result[placement] += content
            return result

        request.get_dynamic_html = get_dynamic_html
