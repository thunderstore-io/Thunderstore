from django.urls import include, path

from thunderstore.community.api.experimental.urls import (
    urls as community_experimental_urls,
)
from thunderstore.frontend.api.experimental.urls import (
    urls as frontend_experimental_urls,
)
from thunderstore.redirects.urls import legacy_api_v1_urls
from thunderstore.repository.api.experimental.urls import (
    urls as repository_experimental_urls,
)
from thunderstore.usermedia.api.experimental.urls import (
    urls as usermedia_experimental_urls,
)

api_experimental_urls = [
    path(
        "",
        include(repository_experimental_urls),
    ),
    path(
        "",
        include(community_experimental_urls),
    ),
    path(
        "",
        include(usermedia_experimental_urls),
    ),
    path(
        "",
        include(frontend_experimental_urls),
    ),
]

api_urls = [
    path("v1/", include((legacy_api_v1_urls, "v1"), namespace="v1")),
    path(
        "experimental/",
        include((api_experimental_urls, "experimental"), namespace="experimental"),
    ),
]
