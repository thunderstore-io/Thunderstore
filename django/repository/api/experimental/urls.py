from django.urls import path

from repository.api.experimental.views import PackageListApiView

urls = [
    path('package/', PackageListApiView.as_view(), name="package-list")
]
