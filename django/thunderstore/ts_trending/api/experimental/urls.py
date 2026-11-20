from django.urls import path

from thunderstore.ts_trending.api.experimental.views import IngestApiView

urls = [
    path(
        "trending/ingest/",
        IngestApiView.as_view(),
        name="trending.ingest",
    ),
]
