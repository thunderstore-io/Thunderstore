from django.urls import path

from thunderstore.social.api.experimental.views import CompleteLoginApiView

urls = [
    path(
        "auth/complete/<slug:provider>/",
        CompleteLoginApiView.as_view(),
        name="auth.complete",
    ),
]
