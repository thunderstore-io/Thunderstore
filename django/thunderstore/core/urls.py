from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from thunderstore.frontend.views import (
    ManifestV1ValidatorView,
    MarkdownPreviewView,
    ads_txt_view,
    robots_txt_view,
)
from thunderstore.github.urls import github_urls
from thunderstore.repository.urls import urlpatterns as repository_urls
from thunderstore.repository.views import PackageListView

from ..community.views import FaviconView
from .api_urls import api_urls
from .healthcheck import healthcheck_view
from .setting_urls import settings_urls

handler404 = "thunderstore.frontend.views.handle404"
handler500 = "thunderstore.frontend.views.handle500"

AUTH_ROOT = "auth/"

special_urls = [
    path("github/", include((github_urls, "github"), namespace="github")),
]

urlpatterns = [
    path("", PackageListView.as_view(), name="index"),
    path("ads.txt", ads_txt_view, name="ads.txt"),
    path("robots.txt", robots_txt_view, name="robots.txt"),
    path(AUTH_ROOT, include("social_django.urls", namespace="social")),
    path("logout/", LogoutView.as_view(), kwargs={"next_page": "/"}, name="logout"),
    path("package/", include(repository_urls)),
    path("settings/", include(settings_urls)),
    path("_/", include((special_urls, "special"), namespace="special")),
    path("favicon.ico", FaviconView.as_view()),
    path("djangoadmin/", admin.site.urls),
    path("healthcheck/", healthcheck_view, name="healthcheck"),
    path("api/", include((api_urls, "api"), namespace="api")),
    path(
        "tools/markdown-preview/",
        MarkdownPreviewView.as_view(),
        name="tools.markdown-preview",
    ),
    path(
        "tools/manifest-v1-validator/",
        ManifestV1ValidatorView.as_view(),
        name="tools.manifest-v1-validator",
    ),
]

schema_view = get_schema_view(
    openapi.Info(
        title="Thunderstore API",
        default_version="v1",
        description=("Schema is automatically generated and not completely accurate."),
        contact=openapi.Contact(
            name="Mythic#0001", url="https://discord.gg/UWpWhjZken"
        ),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns += [
    path("api/docs/", schema_view.with_ui("swagger", cache_timeout=0), name="swagger"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG_TOOLBAR_ENABLED:
    import debug_toolbar

    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns
