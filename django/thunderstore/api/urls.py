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
        name="cyberstorm.community.list",
    ),
    path(
        "community/<str:community_id>/",
        CommunityDetailAPIView.as_view(),
        name="cyberstorm.community.detail",
    ),
    path(
        "team/<str:team_id>/",
        TeamDetailAPIView.as_view(),
        name="cyberstorm.team.detail",
    ),
]
