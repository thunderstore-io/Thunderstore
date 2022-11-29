from django.urls import path

from thunderstore.community.api.experimental.views import (
    CommunitiesExperimentalApiView,
    CurrentCommunityExperimentalApiView,
    PackageCategoriesExperimentalApiView,
    PackageListingUpdateApiView,
)

urls = [
    path(
        "community/",
        CommunitiesExperimentalApiView.as_view(),
        name="communities",
    ),
    path(
        "community/<slug:community>/category/",
        PackageCategoriesExperimentalApiView.as_view(),
        name="categories",
    ),
    path(
        "current-community/",
        CurrentCommunityExperimentalApiView.as_view(),
        name="current-community",
    ),
    path(
        "package-listing/<int:pk>/update/",
        PackageListingUpdateApiView.as_view(),
        name="package-listing.update",
    ),
]
