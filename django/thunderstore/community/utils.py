from thunderstore.community.models import Community


def get_community_for_request(request):
    community = Community.objects.filter(identifier="riskofrain2").first()
    if community:
        return community
    return Community.objects.create(identifier="riskofrain2", name="Risk of Rain 2")
