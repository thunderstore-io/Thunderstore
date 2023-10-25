from django.urls import path

from thunderstore.api.cyberstorm.views import (
    CommunityDetailAPIView,
    CommunityFiltersAPIView,
    CommunityListAPIView,
    TeamDetailAPIView,
    TeamMembersAPIView,
    TeamServiceAccountsAPIView,
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
        "community/<str:community_id>/filters/",
        CommunityFiltersAPIView.as_view(),
        name="cyberstorm.community.filters",
    ),
    path(
        "team/<str:team_id>/",
        TeamDetailAPIView.as_view(),
        name="cyberstorm.team.detail",
    ),
    path(
        "team/<str:team_id>/members/",
        TeamMembersAPIView.as_view(),
        name="cyberstorm.team.members",
    ),
    path(
        "team/<str:team_id>/service-accounts/",
        TeamServiceAccountsAPIView.as_view(),
        name="cyberstorm.team.service-accounts",
    ),
]
