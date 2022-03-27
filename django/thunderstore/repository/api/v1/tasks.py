from thunderstore.community.models import CommunitySite
from thunderstore.repository.api.v1.viewsets import serialize_package_list_for_community
from thunderstore.repository.models.cache import APIV1PackageCache


def update_api_v1_caches() -> None:
    update_api_v1_indexes()


def update_api_v1_indexes() -> None:
    for site in CommunitySite.objects.all():
        APIV1PackageCache.update_for_community(
            community=site.community,
            content=serialize_package_list_for_community(community_site=site),
        )
    APIV1PackageCache.drop_stale_cache()
