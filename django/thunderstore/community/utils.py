from django.contrib.sites.shortcuts import get_current_site

from thunderstore.community.models import Community
from thunderstore.community.models.community_site import CommunitySite


# TODO: Remove and rely on request.community when request is actually available
def get_community_for_request(request):
    community = Community.objects.filter(identifier="riskofrain2").first()
    if community:
        return community
    return Community.objects.create(identifier="riskofrain2", name="Risk of Rain 2")


def get_community_site_for_request(request):
    site = get_current_site(request)
    return CommunitySite.objects.select_related(
        "site", "community"
    ).get(site=site)
