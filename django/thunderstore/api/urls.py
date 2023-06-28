from django.urls import path

from thunderstore.api.cyberstorm.views import PackageVersionDetailAPIView

cyberstorm_urls = [
    path(
        "community/<str:community_id>/package/<str:package_namespace>/<str:package_name>/<str:package_version>/",
        PackageVersionDetailAPIView.as_view(),
        name="cyberstorm.package.version",
    ),
]
