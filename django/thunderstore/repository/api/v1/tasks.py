from thunderstore.community.models import Community, CommunitySite
from thunderstore.core.utils import capture_exception
from thunderstore.repository.api.v1.viewsets import serialize_package_list_for_community
from thunderstore.repository.models import APIV1ChunkedPackageCache, APIV1PackageCache


def update_api_v1_caches() -> None:
    update_api_v1_indexes()


def update_api_v1_indexes() -> None:
    for site in CommunitySite.objects.iterator():
        try:
            APIV1PackageCache.update_for_community(
                community=site.community,
                content=serialize_package_list_for_community(
                    community=site.community,
                ),
            )
        except Exception as e:  # pragma: no cover
            capture_exception(e)
    for community in Community.objects.filter(sites=None).iterator():
        try:
            APIV1PackageCache.update_for_community(
                community=community,
                content=serialize_package_list_for_community(
                    community=community,
                ),
            )
        except Exception as e:  # pragma: no cover
            capture_exception(e)
    APIV1PackageCache.drop_stale_cache()


def update_api_v1_chunked_package_caches() -> None:
    for community in Community.objects.iterator():
        try:
            APIV1ChunkedPackageCache.update_for_community(community)
        except Exception as e:  # pragma: no cover
            capture_exception(e)

    APIV1ChunkedPackageCache.drop_stale_cache()
