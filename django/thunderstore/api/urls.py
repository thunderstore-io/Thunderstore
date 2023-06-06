from django.urls import path

from thunderstore.api.views import CommunitiesAPIView, CommunityAPIView, PackageAPIView, PackagePreviewAPIView

urls = [
    path(
        "c/",
        CommunitiesAPIView.as_view(),  # type: ignore
        name="api.communities",
    ),
    path(
        "c/<slug:community_identifier>/",
        CommunityAPIView.as_view(),  # type: ignore
        name="api.community",
    ),
    path(
        "c/<slug:community_identifier>/p/<slug:package_namespace>/<slug:package_name>/",
        PackageAPIView.as_view(),  # type: ignore
        name="api.package",
    ),
    path(
        "p/",
        PackagePreviewAPIView.as_view(),  # type: ignore
        name="api.packages",
    ),
]
