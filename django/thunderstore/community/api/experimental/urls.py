from django.urls import path

from thunderstore.community.api.experimental.views.category import (
    PackageCategoriesExperimentalApiView,
)
from thunderstore.community.api.experimental.views.community import (
    CommunitiesExperimentalApiView,
    CurrentCommunityExperimentalApiView,
)
from thunderstore.community.api.experimental.views.listing import (
    PackageListingApproveApiView,
    PackageListingRejectApiView,
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
    path(
        "package-listing/<int:pk>/approve/",
        PackageListingApproveApiView.as_view(),
        name="package-listing.approve",
    ),
    path(
        "package-listing/<int:pk>/reject/",
        PackageListingRejectApiView.as_view(),
        name="package-listing.reject",
    ),
]
