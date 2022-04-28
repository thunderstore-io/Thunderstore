from django.urls import path

from thunderstore.repository.views.repository import LegacyUrlRedirectView

legacy_package_urls = [
    path("", LegacyUrlRedirectView.as_view(), name="packages.list"),
    path("create/", LegacyUrlRedirectView.as_view(), name="packages.create"),
    path(
        "create/old/",
        LegacyUrlRedirectView.as_view(),
        name="packages.create.old",
    ),
    path("create/docs/", LegacyUrlRedirectView.as_view(), name="packages.create.docs"),
    path(
        "<str:owner>/<str:name>/",
        LegacyUrlRedirectView.as_view(),
        name="packages.detail",
    ),
    path(
        "<str:owner>/<str:name>/dependants/",
        LegacyUrlRedirectView.as_view(),
        name="packages.list_by_dependency",
    ),
    path(
        "<str:owner>/<str:name>/<str:version>/",
        LegacyUrlRedirectView.as_view(),
        name="packages.version.detail",
    ),
    path(
        "<str:owner>/",
        LegacyUrlRedirectView.as_view(),
        name="packages.list_by_owner",
    ),
]


legacy_api_v1_urls = [
    path(
        "current-user/info/", LegacyUrlRedirectView.as_view(), name="current-user.info"
    ),
    path(
        "bot/deprecate-mod/", LegacyUrlRedirectView.as_view(), name="bot.deprecate-mod"
    ),
    path("package/", LegacyUrlRedirectView.as_view(), name="package-list"),
    path(
        "package/<str:uuid4>/", LegacyUrlRedirectView.as_view(), name="package-detail"
    ),
    path(
        "package/<str:uuid4>/rate/",
        LegacyUrlRedirectView.as_view(),
        name="package-rate",
    ),
]
