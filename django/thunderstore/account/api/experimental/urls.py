from django.urls import path

from thunderstore.account.api.experimental.views import TokenExperimentalApiView

urls = [
    path(
        "auth/token/",
        TokenExperimentalApiView.as_view(),
        name="token",
    ),
]
