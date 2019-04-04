from django.conf import settings
from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.views.generic.base import RedirectView
from django.urls import path, include
from django.http import HttpResponse

from repository.urls import urlpatterns as repository_urls
from repository.views import PackageListView


urlpatterns = [
    path('', PackageListView.as_view(), name="index"),
    path('auth/', include('social_django.urls', namespace='social')),
    path('logout/', LogoutView.as_view(), kwargs={'next_page': '/'}, name="logout"),
    path('package/', include(repository_urls)),
    path('favicon.ico', RedirectView.as_view(url="%s%s" % (settings.STATIC_URL, 'favicon.ico'))),
    path('djangoadmin/', admin.site.urls),
    path('healthcheck/', lambda request: HttpResponse("OK"), name="healthcheck")
]
