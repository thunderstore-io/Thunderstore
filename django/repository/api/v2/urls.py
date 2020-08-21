from django.urls import path

from repository.api.v2.views.package_list import PackageListApiView

urls = [
    path('package/', PackageListApiView.as_view(), name="package-list")
]
