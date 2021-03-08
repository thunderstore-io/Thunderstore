from django.conf import settings


class QueryCountHeaderMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not settings.DEBUG:
            return self.get_response(request)
        else:
            from django.db import connection
            from django.test.utils import CaptureQueriesContext

            with CaptureQueriesContext(connection) as context:
                response = self.get_response(request)
            response["Django-Query-Count"] = len(context)
            return response
