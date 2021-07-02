from django.urls import path

from thunderstore.frontend.api.experimental.views.markdown import RenderMarkdownApiView

urls = [
    path(
        "frontend/render-markdown/",
        RenderMarkdownApiView.as_view(),
        name="frontend.render-markdown",
    ),
]
