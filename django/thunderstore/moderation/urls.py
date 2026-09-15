from django.urls import path

from thunderstore.moderation.markdown import MarkdownChangesAPIView
from thunderstore.plugins.registry import plugin_registry
from thunderstore.repository.views.package.list import PackageReviewListView

moderation_urls = [
    path(
        "api/markdown/changes/",
        MarkdownChangesAPIView.as_view(),
        name="moderation.markdown.changes",
    ),
    path(
        "review-queue/packages/",
        PackageReviewListView.as_view(),
        name="review-queue.packages",
    ),
] + plugin_registry.get_moderation_urls()
