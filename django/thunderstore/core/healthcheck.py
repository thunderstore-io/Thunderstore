import os

from django.http import HttpResponse


def healthcheck_view(request):
    try:
        pid = int(open("/var/run/crond.pid", "r").read())
        os.kill(pid, 0)
        return HttpResponse("OK")
    except Exception:
        return HttpResponse("FAIL", status=500)
