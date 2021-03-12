from django.urls import include, path

from thunderstore.account.api.experimental.urls import urls as account_experimental_urls
from thunderstore.community.api.experimental.urls import (
    urls as community_experimental_urls,
)
from thunderstore.repository.api.experimental.urls import (
    urls as repository_experimental_urls,
)
from thunderstore.repository.api.v1.urls import urls as v1_urls

api_experimental_urls = [
    path(
        "",
        include(
            (repository_experimental_urls, "api-experimental"),
            namespace="api-experimental",
        ),
    ),
    path(
        "",
        include(community_experimental_urls),
    ),
    path(
        "",
        include(account_experimental_urls),
    ),
]

api_urls = [
    path("v1/", include((v1_urls, "v1"), namespace="v1")),
    path(
        "experimental/",
        include((api_experimental_urls, "experimental"), namespace="experimental"),
    ),
]
