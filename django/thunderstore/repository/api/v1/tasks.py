from django.conf import settings
from django.test.client import RequestFactory

from thunderstore.community.middleware import add_community_context_to_request
from thunderstore.community.models import CommunitySite
from thunderstore.repository.api.v1.viewsets import PackageViewSet
from thunderstore.repository.models import Package


def update_api_v1_caches():
    update_api_v1_indexes()
    # TODO: Optimize and enable, or just leave it out of the manual cache
    # update_api_v1_details()


def update_api_v1_indexes():
    for community_site in CommunitySite.objects.all():
        request = RequestFactory().get(
            f"/c/{community_site.community.identifier}/api/v1/package/",
            SERVER_NAME=settings.SERVER_NAME,
        )
        view = PackageViewSet.as_view({"get": "list"})
        PackageViewSet.update_cache(
            view, request, community_identifier=community_site.community.identifier
        )


def update_api_v1_details():
    for community_site in CommunitySite.objects.all():
        for uuid in Package.objects.filter(is_active=True).values_list(
            "uuid4", flat=True
        ):
            view = PackageViewSet.as_view({"get": "retrieve"})
            request = RequestFactory().get(
                f"/c/{community_site.community.identifier}/api/v1/package/{uuid}/",
                SERVER_NAME=settings.SERVER_NAME,
            )
            PackageViewSet.update_cache(
                view,
                request,
                uuid4=uuid,
                community_identifier=community_site.community.identifier,
            )
