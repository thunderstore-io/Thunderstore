from django.urls import path

from thunderstore.moderation.markdown_history import (
    PackageVersionMarkdownHistoryAPIView,
)
from thunderstore.plugins.registry import plugin_registry
from thunderstore.repository.views.package.list import PackageReviewListView

moderation_urls = [
    path(
        "api/package/<str:namespace_id>/<str:package_name>/v/<str:version_number>/markdown/<str:document>/history/",
        PackageVersionMarkdownHistoryAPIView.as_view(),
        name="moderation.package.version.markdown.history",
    ),
    path(
        "review-queue/packages/",
        PackageReviewListView.as_view(),
        name="review-queue.packages",
    ),
] + plugin_registry.get_moderation_urls()
