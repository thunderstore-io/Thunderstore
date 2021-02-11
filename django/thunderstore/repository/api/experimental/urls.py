from django.urls import path

from thunderstore.repository.api.experimental.views import (
    PackageListApiView,
    UploadPackageApiView,
)
from thunderstore.social.api.experimental.views import CurrentUserExperimentalApiView

urls = [
    path(
        "current-user/", CurrentUserExperimentalApiView.as_view(), name="current-user"
    ),
    path("package/", PackageListApiView.as_view(), name="package-list"),
    path("package/upload/", UploadPackageApiView.as_view(), name="package-upload"),
]
