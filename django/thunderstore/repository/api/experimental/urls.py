from django.urls import path

from thunderstore.repository.api.experimental.views import (
    PackageListApiView,
    UploadPackageApiView,
)

urls = [
    path("package/", PackageListApiView.as_view(), name="package-list"),
    path("package/upload/", UploadPackageApiView.as_view(), name="package-upload"),
]
