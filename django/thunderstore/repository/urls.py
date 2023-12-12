from django.urls import include, path, re_path

from thunderstore.plugins.registry import plugin_registry
from thunderstore.repository.api.v1.urls import community_urls as v1_community_urls
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
    SettingsTeamDonationLinkView,
    SettingsTeamLeaveView,
    SettingsTeamListView,
    SettingsTeamServiceAccountView,
)
from thunderstore.repository.views.wiki import (
    PackageWikiHomeView,
    PackageWikiPageDetailView,
    PackageWikiPageEditView,
)

legacy_package_urls = (
    [
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
            "<str:owner>/<str:name>/wiki/",
            PackageWikiHomeView.as_view(),
            name="packages.detail.wiki",
        ),
        path(
            "<str:owner>/<str:name>/wiki/new/",
            PackageWikiPageEditView.as_view(),
            name="packages.detail.wiki.page.new",
        ),
        re_path(
            # Regex pattern is used to resolve any variation of slug usage after
            # page ID, even if the slug is completely incorrect.
            r"(?P<owner>[\w_-]+)/(?P<name>[\w_]+)/wiki/(?P<page>[0-9]+)(?:-(?P<pslug>[\w-]*))?/$",
            PackageWikiPageDetailView.as_view(),
            name="packages.detail.wiki.page.detail",
        ),
        path(
            "<str:owner>/<str:name>/wiki/<int:page>-<slug:pslug>/edit/",
            PackageWikiPageEditView.as_view(),
            name="packages.detail.wiki.page.edit",
        ),
        path(
            "<str:owner>/<str:name>/dependants/",
            PackageListByDependencyView.as_view(),
            name="packages.list_by_dependency",
        ),
        path(
            "<str:owner>/",
            PackageListByOwnerView.as_view(),
            name="packages.list_by_owner",
        ),
    ]
    + plugin_registry.get_legacy_package_urls()
    + [
        path(
            "<str:owner>/<str:name>/<str:version>/",
            PackageVersionDetailView.as_view(),
            name="packages.version.detail",
        ),
    ]
)

package_urls = [
    path("", PackageListView.as_view(), name="packages.list"),
    path("api/v1/", include((v1_community_urls, "api"), namespace="api")),
    path("create/", PackageCreateView.as_view(), name="packages.create"),
    path("create/old/", PackageCreateOldView.as_view(), name="packages.create.old"),
    path("create/docs/", PackageDocsView.as_view(), name="packages.create.docs"),
    path(
        "p/<str:owner>/<str:name>/",
        PackageDetailView.as_view(),
        name="packages.detail",
    ),
    path(
        "p/<str:owner>/<str:name>/wiki/",
        PackageWikiHomeView.as_view(),
        name="packages.detail.wiki",
    ),
    path(
        "p/<str:owner>/<str:name>/wiki/new/",
        PackageWikiPageEditView.as_view(),
        name="packages.detail.wiki.page.new",
    ),
    re_path(
        # Regex pattern is used to resolve any variation of slug usage after
        # page ID, even if the slug is completely incorrect.
        r"p/(?P<owner>[\w_-]+)/(?P<name>[\w_]+)/wiki/(?P<page>[0-9]+)(?:-(?P<pslug>[\w-]*))?/$",
        PackageWikiPageDetailView.as_view(),
        name="packages.detail.wiki.page.detail",
    ),
    path(
        "p/<str:owner>/<str:name>/wiki/<int:page>-<slug:pslug>/edit/",
        PackageWikiPageEditView.as_view(),
        name="packages.detail.wiki.page.edit",
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
] + plugin_registry.get_new_package_urls()

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
    path(
        "teams/<str:name>/donation-link/",
        SettingsTeamDonationLinkView.as_view(),
        name="settings.teams.detail.donation_link",
    ),
]
