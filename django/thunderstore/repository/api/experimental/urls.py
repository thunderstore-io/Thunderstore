from django.urls import path

from thunderstore.repository.api.experimental.views import (
    PackageListApiView,
    UploadPackageApiView,
)

urls = [
    path("package/", PackageListApiView.as_view(), name="package-list"),
    path("package/version/", UploadPackageApiView.as_view(), name="package-version"),
]
