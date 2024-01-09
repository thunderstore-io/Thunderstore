from django.urls import path

from thunderstore.repository.views.package.list import PackageReviewListView

moderation_urls = [
    path(
        "review-queue/packages/",
        PackageReviewListView.as_view(),
        name="review-queue.packages",
    ),
]
