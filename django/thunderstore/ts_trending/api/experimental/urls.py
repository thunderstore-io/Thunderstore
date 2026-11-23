from django.urls import path

from thunderstore.ts_trending.api.experimental.views import (
    IngestApiView,
    TrendingOrderApiView,
)

urls = [
    path(
        "trending/ingest/",
        IngestApiView.as_view(),
        name="trending.ingest",
    ),
    path(
        "trending/order/<slug:community_id>/",
        TrendingOrderApiView.as_view(),
        name="trending.order",
    ),
]
