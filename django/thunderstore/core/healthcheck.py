from django.http import HttpResponse


def healthcheck_view(request):
    return HttpResponse("OK")
