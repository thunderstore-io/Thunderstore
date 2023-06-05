from django.urls import path

from thunderstore.api.views import CommunitiesAPIView, CommunityAPIView

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
]
