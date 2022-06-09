from django.urls import path

from thunderstore.social.api.experimental.views import (
    CompleteLoginApiView,
    ValidateSessionApiView,
)

urls = [
    path(
        "auth/complete/<slug:provider>/",
        CompleteLoginApiView.as_view(),
        name="auth.complete",
    ),
    path(
        "auth/validate/",
        ValidateSessionApiView.as_view(),
        name="auth.validate",
    ),
]
