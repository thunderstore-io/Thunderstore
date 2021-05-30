from django.urls import path

from thunderstore.repository.api.experimental.views import (
    PackageDetailApiView,
    PackageListApiView,
    PackageVersionDetailApiView,
    UploadPackageApiView,
)
from thunderstore.repository.api.experimental.views.submit import SubmitPackageApiView
from thunderstore.social.api.experimental.views import CurrentUserExperimentalApiView

urls = [
    path(
        "current-user/", CurrentUserExperimentalApiView.as_view(), name="current-user"
    ),
    path("package/", PackageListApiView.as_view(), name="package-list"),
    path(
        "package/<str:namespace>/<str:name>/",
        PackageDetailApiView.as_view(),
        name="package-detail",
    ),
    path(
        "package/<str:namespace>/<str:name>/<str:version>/",
        PackageVersionDetailApiView.as_view(),
        name="package-version-detail",
    ),
    path("package/submit/", SubmitPackageApiView.as_view(), name="package-submit"),
    path("package/upload/", UploadPackageApiView.as_view(), name="package-upload"),
]
