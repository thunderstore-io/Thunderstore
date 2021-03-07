from django.urls import path

from thunderstore.community.api.experimental.views import (
    CommunitiesExperimentalApiView,
    PackageCategoriesExperimentalApiView,
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
]
