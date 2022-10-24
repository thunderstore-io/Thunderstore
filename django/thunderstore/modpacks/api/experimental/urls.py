from django.urls import path

from thunderstore.modpacks.api.experimental.views.legacyprofile import (
    LegacyProfileCreateApiView,
    LegacyProfileRetrieveApiView,
)

urls = [
    path(
        "legacyprofile/create/",
        LegacyProfileCreateApiView.as_view(),
        name="legacyprofile.create",
    ),
    path(
        "legacyprofile/get/<uuid:key>/",
        LegacyProfileRetrieveApiView.as_view(),
        name="legacyprofile.retrieve",
    ),
]
