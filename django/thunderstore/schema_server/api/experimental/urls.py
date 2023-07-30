from django.urls import path

from thunderstore.schema_server.api.experimental.views.channel import (
    SchemaChannelApiView,
    SchemaChannelLatestApiView,
)

urls = [
    path(
        "schema/<str:channel>/",
        SchemaChannelApiView.as_view(),
        name="schema.channel",
    ),
    path(
        "schema/<str:channel>/latest/",
        SchemaChannelLatestApiView.as_view(),
        name="schema.channel.latest",
    ),
]
