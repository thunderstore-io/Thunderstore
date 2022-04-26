from django.utils.functional import cached_property

from thunderstore.community.models.community import Community
from thunderstore.community.models.community_site import CommunitySite


class CommunityMixin:
    @cached_property
    def community_identifier(self):
        return (
            self.kwargs.get("community_identifier", None)
            or self.request.community.identifier
        )

    @cached_property
    def community(self):
        return Community.objects.get(identifier=self.community_identifier)

    @cached_property
    def community_site(self):
        return CommunitySite.objects.get(community=self.community)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["community_identifier"] = self.community_identifier
        context["community"] = self.community
        return context
