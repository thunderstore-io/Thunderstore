from django.urls import path

from thunderstore.wiki.api.experimental.views import WikiPageApiView

urls = [
    path(
        "page/<str:pk>/",
        WikiPageApiView.as_view(),
        name="page.detail",
    ),
]
