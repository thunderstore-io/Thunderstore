from django.urls import path

from thunderstore.repository.views import (
    PackageCreateOldView,
    PackageCreateView,
    PackageDetailView,
    PackageDocsView,
    PackageDownloadView,
    PackageListByDependencyView,
    PackageListByOwnerView,
    PackageListView,
    PackageVersionDetailView,
)
from thunderstore.repository.views.team_settings import (
    SettingsTeamAddMemberView,
    SettingsTeamAddServiceAccountView,
    SettingsTeamCreateView,
    SettingsTeamDetailView,
    SettingsTeamDisbandView,
    SettingsTeamLeaveView,
    SettingsTeamListView,
    SettingsTeamServiceAccountView,
)

legacy_package_urls = [
    path("", PackageListView.as_view(), name="packages.list"),
    path("create/", PackageCreateView.as_view(), name="packages.create"),
    path(
        "create/old/",
        PackageCreateOldView.as_view(),
        name="packages.create.old",
    ),
    path("create/docs/", PackageDocsView.as_view(), name="packages.create.docs"),
    path(
        "download/<str:owner>/<str:name>/<str:version>/",
        PackageDownloadView.as_view(),
        name="packages.download",
    ),
    path(
        "<str:owner>/<str:name>/",
        PackageDetailView.as_view(),
        name="packages.detail",
    ),
    path(
        "<str:owner>/<str:name>/dependants/",
        PackageListByDependencyView.as_view(),
        name="packages.list_by_dependency",
    ),
    path(
        "<str:owner>/<str:name>/<str:version>/",
        PackageVersionDetailView.as_view(),
        name="packages.version.detail",
    ),
    path(
        "<str:owner>/",
        PackageListByOwnerView.as_view(),
        name="packages.list_by_owner",
    ),
]

package_urls = [
    path("", PackageListView.as_view(), name="packages.list"),
    path("create/", PackageCreateView.as_view(), name="packages.create"),
    path("create/old/", PackageCreateOldView.as_view(), name="packages.create.old"),
    path("create/docs/", PackageDocsView.as_view(), name="packages.create.docs"),
    path(
        "p/<str:owner>/<str:name>/",
        PackageDetailView.as_view(),
        name="packages.detail",
    ),
    path(
        "p/<str:owner>/<str:name>/dependants/",
        PackageListByDependencyView.as_view(),
        name="packages.list_by_dependency",
    ),
    path(
        "p/<str:owner>/<str:name>/v/<str:version>/",
        PackageVersionDetailView.as_view(),
        name="packages.version.detail",
    ),
    path(
        "p/<str:owner>/",
        PackageListByOwnerView.as_view(),
        name="packages.list_by_owner",
    ),
]

settings_urls = [
    path(
        "teams/",
        SettingsTeamListView.as_view(),
        name="settings.teams",
    ),
    path(
        "teams/create/",
        SettingsTeamCreateView.as_view(),
        name="settings.teams.create",
    ),
    path(
        "teams/<str:name>/",
        SettingsTeamDetailView.as_view(),
        name="settings.teams.detail",
    ),
    path(
        "teams/<str:name>/add-member/",
        SettingsTeamAddMemberView.as_view(),
        name="settings.teams.detail.add_member",
    ),
    path(
        "teams/<str:name>/service-accounts/",
        SettingsTeamServiceAccountView.as_view(),
        name="settings.teams.detail.service_accounts",
    ),
    path(
        "teams/<str:name>/add-service-account/",
        SettingsTeamAddServiceAccountView.as_view(),
        name="settings.teams.detail.add_service_account",
    ),
    path(
        "teams/<str:name>/leave/",
        SettingsTeamLeaveView.as_view(),
        name="settings.teams.detail.leave",
    ),
    path(
        "teams/<str:name>/disband/",
        SettingsTeamDisbandView.as_view(),
        name="settings.teams.detail.disband",
    ),
]
