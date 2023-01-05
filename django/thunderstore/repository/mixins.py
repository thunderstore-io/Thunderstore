from django.http import Http404
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
        try:
            return Community.objects.get(identifier=self.community_identifier)
        except Community.DoesNotExist:
            raise Http404()

    @cached_property
    def community_site(self):
        return CommunitySite.objects.get(community=self.community)

    @cached_property
    def use_old_urls(self):
        return not bool(self.kwargs.get("community_identifier", False))

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["community_identifier"] = self.community_identifier
        context["community"] = self.community
        if self.community.sites.first():
            context["community_site"] = self.community_site
        context["use_old_urls"] = self.use_old_urls
        return context

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.setdefault("community", self.community)
        return context
