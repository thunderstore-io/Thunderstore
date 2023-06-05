from django.urls import include, path

from thunderstore.api.urls import urls as cyberstorm_urls
from thunderstore.community.api.experimental.urls import (
    urls as community_experimental_urls,
)
from thunderstore.frontend.api.experimental.urls import (
    urls as frontend_experimental_urls,
)
from thunderstore.modpacks.api.experimental.urls import (
    urls as modpacks_experimental_urls,
)
from thunderstore.repository.api.experimental.urls import (
    urls as repository_experimental_urls,
)
from thunderstore.repository.api.v1.urls import urls as v1_urls
from thunderstore.social.api.experimental.urls import urls as social_experimental_urls
from thunderstore.usermedia.api.experimental.urls import (
    urls as usermedia_experimental_urls,
)
from thunderstore.wiki.api.experimental.urls import urls as wiki_experimental_urls

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
    path(
        "",
        include(social_experimental_urls),
    ),
    path(
        "",
        include(modpacks_experimental_urls),
    ),
    path(
        "wiki/",
        include(wiki_experimental_urls),
    ),
]

api_urls = [
    path("v1/", include((v1_urls, "v1"), namespace="v1")),
    path(
        "experimental/",
        include((api_experimental_urls, "experimental"), namespace="experimental"),
    ),
    path(
        "cyberstorm/",
        include((cyberstorm_urls, "cyberstorm"), namespace="cyberstorm"),
    ),
]
