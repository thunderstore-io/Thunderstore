from django.urls import include, path

from thunderstore.community.views import CommunitiesView
from thunderstore.repository.urls import urlpatterns as package_urls

community_urls = [
    path("", CommunitiesView.as_view(), name="communities"),
    path("<str:community_identifier>/", include(package_urls), name="community"),
]
