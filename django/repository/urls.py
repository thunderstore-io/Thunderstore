from django.urls import path

from repository.views import PackageListView
from repository.views import PackageDetailView
from repository.views import PackageCreateView
from repository.views import PackageDownloadView
from repository.views import PackageListByOwnerView
from repository.views import PackageListByDependencyView


urlpatterns = [
    path(
        '',
        PackageListView.as_view(),
        name="packages.list"
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
    ),
    path(
        '<str:owner>/<str:name>/',
        PackageDetailView.as_view(),
        name="packages.detail"
    ),
    path(
        '<str:owner>/<str:name>/dependants/',
        PackageListByDependencyView.as_view(),
        name="packages.list_by_dependency"
    ),
    path(
        '<str:owner>/',
        PackageListByOwnerView.as_view(),
        name="packages.list_by_owner",
    ),
]
