from django.urls import path

from thunderstore.account.api.experimental.views import TokenExperimentalApiView

urls = [
    path(
        "auth/session-token/",
        TokenExperimentalApiView.as_view(),
        name="token",
    ),
]
