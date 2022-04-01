from django.urls import path

from thunderstore.repository.views.repository import LegacyUrlRedirectView

legacy_package_urls = [
    path("", LegacyUrlRedirectView.as_view()),
    path("create/", LegacyUrlRedirectView.as_view()),
    path("create/old/", LegacyUrlRedirectView.as_view()),
    path("create/docs/", LegacyUrlRedirectView.as_view()),
    path(
        "download/<str:owner>/<str:name>/<str:version>/",
        LegacyUrlRedirectView.as_view(),
    ),
    path(
        "<str:owner>/<str:name>/",
        LegacyUrlRedirectView.as_view(),
    ),
    path(
        "<str:owner>/<str:name>/dependants/",
        LegacyUrlRedirectView.as_view(),
    ),
    path(
        "<str:owner>/<str:name>/<str:version>/",
        LegacyUrlRedirectView.as_view(),
    ),
    path(
        "<str:owner>/",
        LegacyUrlRedirectView.as_view(),
    ),
]


legacy_api_v1_urls = [
    path("current-user/info/", LegacyUrlRedirectView.as_view()),
    path("bot/deprecate-mod/", LegacyUrlRedirectView.as_view()),
    path("package/", LegacyUrlRedirectView.as_view()),
    path("package/<str:uuid4>/", LegacyUrlRedirectView.as_view()),
    path("package/<str:uuid4>/rate/", LegacyUrlRedirectView.as_view()),
]
