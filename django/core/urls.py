from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.views.generic.base import RedirectView
from django.urls import path


from frontend.views import IndexView


urlpatterns = [
    path('', IndexView.as_view()),
    path('favicon.ico', RedirectView.as_view(url="%s%s" % (settings.STATIC_URL, 'favicon.ico'))),
    path('djangoadmin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
