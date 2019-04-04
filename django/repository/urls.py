from django.urls import path

from repository.views import PackageListView
from repository.views import PackageDetailView
from repository.views import PackageCreateView
from repository.views import PackageDownloadView
from repository.views import PackageListByOwnerView


urlpatterns = [
    path(
        'list/',
        PackageListView.as_view(),
        name="packages.list"
    ),
    path(
        'view/<int:pk>/',
        PackageDetailView.as_view(),
        name="packages.detail"
    ),
    path(
        'list-by-owner/<str:owner>/',
        PackageListByOwnerView.as_view(),
        name="packages.list_by_owner",
    ),
    path(
        'create/',
        PackageCreateView.as_view(),
        name="packages.create"
    ),
    path(
        'download/<str:owner>/<str:name>/<str:version>/',
        PackageDownloadView.as_view(),
        name="packages.download"
    )
]
