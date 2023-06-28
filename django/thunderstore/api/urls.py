from django.urls import path

from thunderstore.api.cyberstorm.views import PackageListAPIView

cyberstorm_urls = [
    path(
        "package/",
        PackageListAPIView.as_view(),
        name="cyberstorm.packages",
    ),
]
