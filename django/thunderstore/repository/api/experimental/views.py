import json

from django.http import HttpResponse
from rest_framework.generics import ListAPIView
from rest_framework.schemas import AutoSchema

from thunderstore.community.models import CommunitySite, PackageListing, Q
from thunderstore.core.cache import (
    BackgroundUpdatedCacheMixin,
    CacheBustCondition,
    cache_function_result,
)
from thunderstore.core.utils import CommunitySiteSerializerContext
from thunderstore.repository.api.experimental.serializers import (
    PackageListingSerializerExperimental,
)


@cache_function_result(cache_until=CacheBustCondition.any_package_updated)
def get_mod_list_queryset(community_site: CommunitySite):
    return (
        PackageListing.objects.active()
        .exclude(~Q(community=community_site.community))
        .select_related(
            "package",
            "package__owner",
            "package__latest",
        )
        .prefetch_related(
            "package__latest__dependencies",
        )
        .order_by(
            "-package__is_pinned", "package__is_deprecated", "-package__date_updated"
        )
    )


class PackageListSchema(AutoSchema):
    pass


class PackageListApiView(
    BackgroundUpdatedCacheMixin, CommunitySiteSerializerContext, ListAPIView
):
    """
    Lists all available packages
    """

    cache_until = CacheBustCondition.any_package_updated
    serializer_class = PackageListingSerializerExperimental
    schema = PackageListSchema()

    @classmethod
    def get_no_cache_response(cls):
        return HttpResponse(
            json.dumps({"error": "No cache available"}),
            status=503,
            content_type="application/json",
        )

    def get_queryset(self):
        return get_mod_list_queryset(self.request.community_site)
