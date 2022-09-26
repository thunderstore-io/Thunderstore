from django.urls import path

from thunderstore.community.api.experimental.views import (
    CommunitiesExperimentalApiView,
    CurrentCommunityExperimentalApiView,
    PackageCategoriesExperimentalApiView,
    PackageValidationExperimentalApiView,
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
        "community/<slug:community_id>/validate-packages/",
        PackageValidationExperimentalApiView.as_view(),
        name="validate-packages",
    ),
    path(
        "current-community/",
        CurrentCommunityExperimentalApiView.as_view(),
        name="current-community",
    ),
]
