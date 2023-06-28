from django.urls import path

from thunderstore.api.cyberstorm.views import (
    CommunityDetailAPIView,
    CommunityListAPIView,
    PackageDetailAPIView,
    PackageListAPIView,
    PackageVersionDetailAPIView,
    TeamDetailAPIView,
)

cyberstorm_urls = [
    path(
        "community/",
        CommunityListAPIView.as_view(),
        name="cyberstorm.communities",
    ),
    path(
        "community/<str:community_id>/",
        CommunityDetailAPIView.as_view(),
        name="cyberstorm.community",
    ),
    path(
        "community/<str:community_id>/package/<str:package_namespace>/<str:package_name>/",
        PackageDetailAPIView.as_view(),
        name="cyberstorm.package",
    ),
    path(
        "community/<str:community_id>/package/<str:package_namespace>/<str:package_name>/<str:package_version>/",
        PackageVersionDetailAPIView.as_view(),
        name="cyberstorm.package.version",
    ),
    path(
        "package/",
        PackageListAPIView.as_view(),
        name="cyberstorm.packages",
    ),
    path(
        "team/<str:name>/",
        TeamDetailAPIView.as_view(),
        name="cyberstorm.team",
    ),
]
