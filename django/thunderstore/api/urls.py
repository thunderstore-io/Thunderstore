from django.urls import path

from thunderstore.api.cyberstorm.views import (
    CommunityDetailAPIView,
    CommunityListAPIView,
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
        "team/<str:name>/",
        TeamDetailAPIView.as_view(),
        name="cyberstorm.team",
    ),
]
