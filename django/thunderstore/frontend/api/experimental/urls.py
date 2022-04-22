from django.urls import path

from thunderstore.frontend.api.experimental.views import (
    CommunityPackageListApiView,
    FrontPageApiView,
    PackageDetailApiView,
    RenderMarkdownApiView,
)

urls = [
    path(
        "frontend/c/<slug:community_identifier>/packages/",
        CommunityPackageListApiView.as_view(),
        name="frontend.community.packages",
    ),
    path(
        "frontend/c/<slug:community_identifier>/p/<slug:package_namespace>/<slug:package_name>/",
        PackageDetailApiView.as_view(),
        name="frontend.community.package",
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
