from django.urls import path, include

from rest_framework import routers
from repository.api.v1.viewsets import PackageViewSet

from social.api.v1.views.current_user import CurrentUserInfoView

from repository.api.v1.views import DeprecateModApiView
from repository.api.v2.views.package_list import PackageListApiView


v1_router = routers.DefaultRouter()
v1_router.register(r'package', PackageViewSet, basename="package")

api_v1_urls = [
    path('current-user/info/', CurrentUserInfoView.as_view(), name="current-user.info"),
    path('bot/deprecate-mod/', DeprecateModApiView.as_view(), name="bot.deprecate-mod"),
    path('', include(v1_router.urls)),
]

api_v2_urls = [
    path('package/', PackageListApiView.as_view(), name="package-list")
]
