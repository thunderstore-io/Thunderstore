from django.http import HttpResponse
from django.shortcuts import render

from social_core.exceptions import AuthAlreadyAssociated, AuthFailed


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

        if template:
            return HttpResponse(render(request, template))
        return None
