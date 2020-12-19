from django.test.client import RequestFactory

from thunderstore.community.middleware import add_community_context_to_request
from thunderstore.community.models import CommunitySite
from thunderstore.repository.api.v1.viewsets import PackageViewSet
from thunderstore.repository.models import Package


def update_api_v1_caches():
    update_api_v1_indexes()
    update_api_v1_details()


def update_api_v1_indexes():
    for community_site in CommunitySite.objects.all():
        request = RequestFactory().get(
            "/api/v1/package/", SERVER_NAME=community_site.site.domain
        )
        # TODO: Somehow use middleware instead
        add_community_context_to_request(request)
        view = PackageViewSet.as_view({"get": "list"})
        PackageViewSet.update_cache(view, request)


def update_api_v1_details():
    for community_site in CommunitySite.objects.all():
        for uuid in Package.objects.filter(is_active=True).values_list(
            "uuid4", flat=True
        ):
            view = PackageViewSet.as_view({"get": "retrieve"})
            request = RequestFactory().get(
                f"/api/v1/package/{uuid}/", SERVER_NAME=community_site.site.domain
            )
            # TODO: Somehow use middleware instead
            add_community_context_to_request(request)
            PackageViewSet.update_cache(view, request, uuid4=uuid)
