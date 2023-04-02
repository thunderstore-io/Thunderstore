from django.urls import path

from thunderstore.modpacks.api.experimental.views.legacyprofile import (
    LegacyProfileCreateApiView,
    LegacyProfileRetrieveApiView,
)
from thunderstore.modpacks.api.experimental.views.legacyprofilemetadata import LegacyProfileMetaDataRetrieveApiView

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
    path(
        "legacyprofilemetadata/get/<uuid:key>/",
        LegacyProfileMetaDataRetrieveApiView.as_view(),
        name="legacyprofilemetadata.retrieve",
    ),
]
