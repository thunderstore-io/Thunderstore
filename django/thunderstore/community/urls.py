from django.urls import include, path
from django.views.generic.base import RedirectView

from thunderstore.repository.api.v1.urls import urls as v1_urls
from thunderstore.repository.urls import urlpatterns as package_urls

community_urls = [
    path("", RedirectView.as_view(pattern_name="communities")),
    path("<str:community_identifier>/", include(package_urls), name="community"),
    path("<str:community_identifier>/api/v1/", include(v1_urls), name="api.v1"),
]
