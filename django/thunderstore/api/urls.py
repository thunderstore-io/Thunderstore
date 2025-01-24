from django.urls import path

from thunderstore.api.cyberstorm.views import (
    CommunityAPIView,
    CommunityFiltersAPIView,
    CommunityListAPIView,
    DeprecatePackageAPIView,
    PackageListingAPIView,
    PackageListingByCommunityListAPIView,
    PackageListingByDependencyListAPIView,
    PackageListingByNamespaceListAPIView,
    PackagePermissionsAPIView,
    PackageVersionChangelogAPIView,
    PackageVersionListAPIView,
    PackageVersionReadmeAPIView,
    RatePackageAPIView,
    TeamAPIView,
    TeamMemberAddAPIView,
    TeamMemberListAPIView,
    TeamServiceAccountListAPIView,
)

cyberstorm_urls = [
    path(
        "community/",
        CommunityListAPIView.as_view(),
        name="cyberstorm.community.list",
    ),
    path(
        "community/<str:community_id>/",
        CommunityAPIView.as_view(),
        name="cyberstorm.community",
    ),
    path(
        "community/<str:community_id>/filters/",
        CommunityFiltersAPIView.as_view(),
        name="cyberstorm.community.filters",
    ),
    path(
        "listing/<str:community_id>/",
        PackageListingByCommunityListAPIView.as_view(),
        name="cyberstorm.listing.by-community-list",
    ),
    path(
        "listing/<str:community_id>/<str:namespace_id>/",
        PackageListingByNamespaceListAPIView.as_view(),
        name="cyberstorm.listing.by-namespace-list",
    ),
    path(
        "listing/<str:community_id>/<str:namespace_id>/<str:package_name>/",
        PackageListingAPIView.as_view(),
        name="cyberstorm.listing",
    ),
    path(
        "listing/<str:community_id>/<str:namespace_id>/<str:package_name>/dependants/",
        PackageListingByDependencyListAPIView.as_view(),
        name="cyberstorm.listing.by-dependency-list",
    ),
    path(
        "package/<str:namespace_id>/<str:package_name>/latest/changelog/",
        PackageVersionChangelogAPIView.as_view(),
        name="cyberstorm.package.latest.changelog",
    ),
    path(
        "package/<str:namespace_id>/<str:package_name>/latest/readme/",
        PackageVersionReadmeAPIView.as_view(),
        name="cyberstorm.package.latest.readme",
    ),
    path(
        "package/<str:namespace_id>/<str:package_name>/v/<str:version_number>/changelog/",
        PackageVersionChangelogAPIView.as_view(),
        name="cyberstorm.package.version.changelog",
    ),
    path(
        "package/<str:namespace_id>/<str:package_name>/v/<str:version_number>/readme/",
        PackageVersionReadmeAPIView.as_view(),
        name="cyberstorm.package.version.readme",
    ),
    path(
        "package/<str:namespace_id>/<str:package_name>/versions/",
        PackageVersionListAPIView.as_view(),
        name="cyberstorm.package.versions",
    ),
    path(
        "package/<str:namespace_id>/<str:package_name>/rate/",
        RatePackageAPIView.as_view(),
        name="cyberstorm.package.rate",
    ),
    path(
        "package/<str:namespace_id>/<str:package_name>/deprecate/",
        DeprecatePackageAPIView.as_view(),
        name="cyberstorm.package.deprecate",
    ),
    path(
        "package/<str:namespace_id>/<str:package_name>/permissions/",
        PackagePermissionsAPIView.as_view(),
        name="cyberstorm.package.permissions",
    ),
    path(
        "team/<str:team_id>/",
        TeamAPIView.as_view(),
        name="cyberstorm.team",
    ),
    path(
        "team/<str:team_id>/member/",
        TeamMemberListAPIView.as_view(),
        name="cyberstorm.team.member.list",
    ),
    path(
        "team/<str:team_name>/member/add/",
        TeamMemberAddAPIView.as_view(),
        name="cyberstorm.team.member.add",
    ),
    path(
        "team/<str:team_id>/service-account/",
        TeamServiceAccountListAPIView.as_view(),
        name="cyberstorm.team.service-account",
    ),
]
