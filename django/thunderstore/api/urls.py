from django.urls import path

from thunderstore.api.cyberstorm.views import LikePackageAPIView

cyberstorm_urls = [
    path(
        "package/like/<str:uuid4>",
        LikePackageAPIView.as_view(),
        name="cyberstorm.like_package",
    ),
]
