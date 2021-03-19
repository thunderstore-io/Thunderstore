from django.urls import path

from thunderstore.account.api.experimental.views import (
    CreateSessionTokenExperimentalApiView,
)

urls = [
    path(
        "auth/session-token/",
        CreateSessionTokenExperimentalApiView.as_view(),
        name="token",
    ),
]
