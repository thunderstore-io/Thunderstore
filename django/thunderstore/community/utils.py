from typing import Optional

from django.contrib.sites.shortcuts import get_current_site

from thunderstore.community.models import Community, CommunitySite
from thunderstore.repository.models import Package


# TODO: Remove and rely on request.community when request is actually available
def get_community_for_request(request):
    community = Community.objects.filter(identifier="riskofrain2").first()
    if community:
        return community
    return Community.objects.create(identifier="riskofrain2", name="Risk of Rain 2")


def get_community_site_for_request(request):
    site = get_current_site(request)
    return CommunitySite.objects.select_related("site", "community").get(site=site)


def get_preferred_community(
    package: Package, preferred: Community
) -> Optional[Community]:
    """
    Try to return a Community where the Package is listed

    When linking from a Package to its dependency, we'd prefer to link
    to one that's listed on the same Community, but that's not always
    possible. In such case use first available Community.
    """
    listings = package.community_listings.all()

    if not listings:
        return None

    if any(l.community_id == preferred.pk for l in listings):
        return preferred

    return listings[0].community
