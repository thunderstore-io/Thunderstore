from django.urls import path, include


from thunderstore.repository.api.v1.urls import urls as v1_urls
from thunderstore.repository.api.v2.urls import urls as v2_urls
from thunderstore.repository.api.experimental.urls import urls as experimental_urls


api_experimental_urls = [
    path('', include((experimental_urls, "api-experimental"), namespace="api-experimental")),
]

api_urls = [
    path('v1/', include((v1_urls, "v1"), namespace="v1")),
    path('v2/', include((v2_urls, "v2"), namespace="v2")),
    path('experimental/', include((api_experimental_urls, "experimental"), namespace="experimental")),
]
