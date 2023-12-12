from django.urls import include, path
from rest_framework import routers

from thunderstore.repository.api.v1.views.deprecate import DeprecateModApiView
from thunderstore.repository.api.v1.views.metrics import (
    PackageMetricsApiView,
    PackageVersionMetricsApiView,
)
from thunderstore.repository.api.v1.viewsets import PackageViewSet
from thunderstore.social.api.v1.views.current_user import CurrentUserInfoView

v1_router = routers.DefaultRouter()
v1_router.register(r"package", PackageViewSet, basename="package")

urls = [
    path("current-user/info/", CurrentUserInfoView.as_view(), name="current-user.info"),
    path("bot/deprecate-mod/", DeprecateModApiView.as_view(), name="bot.deprecate-mod"),
    path(
        "package-metrics/<str:namespace>/<str:name>/",
        PackageMetricsApiView.as_view(),
        name="package-metrics.package",
    ),
    path(
        "package-metrics/<str:namespace>/<str:name>/<str:version>/",
        PackageVersionMetricsApiView.as_view(),
        name="package-metrics.package-version",
    ),
    path("", include(v1_router.urls)),
]
