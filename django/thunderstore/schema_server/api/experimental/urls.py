from django.urls import path

from thunderstore.schema_server.api.experimental.views.channel import (
    SchemaChannelApiView,
)

urls = [
    path(
        "schema/<str:channel>/",
        SchemaChannelApiView.as_view(),
        name="schema.channel",
    ),
]
