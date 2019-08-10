from django.urls import path, include

from rest_framework import routers
from repository.api.v1.viewsets import PackageViewSet

from social.api.v1.views.current_user import CurrentUserInfoView


v1_router = routers.DefaultRouter()
v1_router.register(r'package', PackageViewSet, basename="package")

api_v1_urls = [
    path('current-user/info/', CurrentUserInfoView.as_view(), name="current-user.info"),
    path('', include(v1_router.urls)),
]
