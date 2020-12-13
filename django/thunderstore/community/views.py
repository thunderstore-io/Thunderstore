from django.conf import settings
from django.shortcuts import redirect
from django.views import View


class FaviconView(View):

    def get(self, *args, **kwargs):
        if self.request.community_site.favicon:
            return redirect(self.request.community_site.favicon.url)
        return redirect(f"{settings.STATIC_URL}favicon.ico")
