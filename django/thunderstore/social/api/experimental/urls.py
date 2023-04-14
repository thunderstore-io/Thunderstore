from django.urls import path

from thunderstore.social.api.experimental.views import (
    CompleteLoginApiView,
    OverwolfLoginApiView,
    OverwolfLogoutApiView,
    ValidateSessionApiView,
)

urls = [
    path(
        "auth/complete/<slug:provider>/",
        CompleteLoginApiView.as_view(),
        name="auth.complete",
    ),
    path(
        "auth/overwolf/login/",
        OverwolfLoginApiView.as_view(),
        name="auth.overwolf.login",
    ),
    path(
        "auth/overwolf/logout/",
        OverwolfLogoutApiView.as_view(),
        name="auth.overwolf.logout",
    ),
    path(
        "auth/validate/",
        ValidateSessionApiView.as_view(),
        name="auth.validate",
    ),
]
