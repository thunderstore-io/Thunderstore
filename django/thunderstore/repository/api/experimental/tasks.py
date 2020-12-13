from django.test.client import RequestFactory

from thunderstore.community.middleware import add_community_context_to_request
from thunderstore.community.models import CommunitySite

from thunderstore.repository.api.experimental.views import PackageListApiView


def update_api_experimental_caches():
    for community_site in CommunitySite.objects.all():
        request = RequestFactory().get("/api/experimental/package/", SERVER_NAME=community_site.site.domain)
        # TODO: Somehow use middleware instead
        add_community_context_to_request(request)
        view = PackageListApiView.as_view()
        PackageListApiView.update_cache(view, request)
