from django.urls import path

from thunderstore.api.views import CommunitiesAPIView, CommunityAPIView, PackageAPIView, PackagePreviewAPIView, TeamAPIView, UserAPIView

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
    path(
        "t/<slug:team_identifier>/",
        TeamAPIView.as_view(),  # type: ignore
        name="api.team",
    ),
    path(
        "u/<slug:user_identifier>/",
        UserAPIView.as_view(),  # type: ignore
        name="api.user",
    ),
]
