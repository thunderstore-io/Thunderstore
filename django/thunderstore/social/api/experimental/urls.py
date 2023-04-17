from django.urls import path

from thunderstore.social.api.experimental.views import (
    CompleteLoginApiView,
    DeleteSessionApiView,
    OverwolfLoginApiView,
    ValidateSessionApiView,
)

urls = [
    path(
        "auth/complete/<slug:provider>/",
        CompleteLoginApiView.as_view(),
        name="auth.complete",
    ),
    path(
        "auth/delete/",
        DeleteSessionApiView.as_view(),
        name="auth.delete",
    ),
    path(
        "auth/overwolf/login/",
        OverwolfLoginApiView.as_view(),
        name="auth.overwolf.login",
    ),
    path(
        "auth/validate/",
        ValidateSessionApiView.as_view(),
        name="auth.validate",
    ),
]
