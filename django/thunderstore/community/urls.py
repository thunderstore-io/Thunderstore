from django.urls import include, path

from thunderstore.repository.urls import package_urls

community_urls = [
    path(
        "<str:community_identifier>/",
        include((package_urls, "community"), namespace="community"),
    ),
]
