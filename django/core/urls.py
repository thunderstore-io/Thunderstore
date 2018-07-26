from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.views.generic.base import RedirectView
from django.urls import path


from frontend.views import IndexView

from repository.views import PackageListView
from repository.views import PackageDetailView
from repository.views import PackageCreateView


urlpatterns = [
    path('', IndexView.as_view(), name="index"),
    path('list/', PackageListView.as_view(), name="packages.list"),
    path('package/<int:pk>/', PackageDetailView.as_view(), name="packages.detail"),
    path('package/create/', PackageCreateView.as_view(), name="packages.create"),
    path('favicon.ico', RedirectView.as_view(url="%s%s" % (settings.STATIC_URL, 'favicon.ico'))),
    path('djangoadmin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
