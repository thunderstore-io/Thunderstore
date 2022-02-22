from django.urls import path

from thunderstore.frontend.api.experimental.views import (
    CommunityPackageListApiView,
    FrontPageApiView,
    RenderMarkdownApiView,
)

urls = [
    path(
        "frontend/c/<slug:community_identifier>/packages/",
        CommunityPackageListApiView.as_view(),
        name="frontend.community.packages",
    ),
    path(
        "frontend/frontpage/",
        FrontPageApiView.as_view(),
        name="frontend.frontpage",
    ),
    path(
        "frontend/render-markdown/",
        RenderMarkdownApiView.as_view(),
        name="frontend.render-markdown",
    ),
]
