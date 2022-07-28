from django.conf import settings
from django.shortcuts import redirect
from django.views import View


class FaviconView(View):
    def get(self, *args, **kwargs):
        return redirect(f"{settings.STATIC_URL}favicon.ico")
