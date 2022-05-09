from thunderstore.community.models import Community, CommunitySite
from thunderstore.repository.api.v1.viewsets import serialize_package_list_for_community
from thunderstore.repository.models.cache import APIV1PackageCache


def update_api_v1_caches() -> None:
    update_api_v1_indexes()


def update_api_v1_indexes() -> None:
    for site in CommunitySite.objects.iterator():
        APIV1PackageCache.update_for_community(
            community=site.community,
            content=serialize_package_list_for_community(
                community=site.community,
                community_site=site,
            ),
        )
    for community in Community.objects.filter(sites=None).iterator():
        APIV1PackageCache.update_for_community(
            community=community,
            content=serialize_package_list_for_community(
                community=community,
                community_site=None,
            ),
        )
    APIV1PackageCache.drop_stale_cache()
