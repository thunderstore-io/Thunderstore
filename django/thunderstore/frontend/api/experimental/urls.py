from django.urls import path

from thunderstore.frontend.api.experimental.views import (
    FrontPageApiView,
    RenderMarkdownApiView,
)

urls = [
    path(
        "frontend/frontpage/",
        FrontPageApiView.as_view(),
        name="frontend.frontpage",
    ),
    path(
        "frontend/render-markdown/",
        RenderMarkdownApiView.as_view(),
        name="frontend.render-markdown",
    ),
]
