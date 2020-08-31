from django.urls import path

from thunderstore.repository.views import PackageListView
from thunderstore.repository.views import PackageDetailView
from thunderstore.repository.views import PackageCreateView
from thunderstore.repository.views import PackageDownloadView
from thunderstore.repository.views import PackageListByOwnerView
from thunderstore.repository.views import PackageListByDependencyView
from thunderstore.repository.views import PackageVersionDetailView


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
        '<str:owner>/<str:name>/<str:version>/',
        PackageVersionDetailView.as_view(),
        name="packages.version.detail",
    ),
    path(
        '<str:owner>/',
        PackageListByOwnerView.as_view(),
        name="packages.list_by_owner",
    ),
]
