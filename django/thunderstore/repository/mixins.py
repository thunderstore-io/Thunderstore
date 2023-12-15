from typing import Optional

from django.db.models import Prefetch
from django.http import Http404
from django.utils.functional import cached_property

from thunderstore.community.context_processors import get_community_context
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
    def community(self) -> Community:
        try:
            site_qs = CommunitySite.objects.select_related("site")
            return Community.objects.prefetch_related(
                Prefetch("sites", queryset=site_qs)
            ).get(identifier=self.community_identifier)
        except Community.DoesNotExist:
            raise Http404()

    @cached_property
    def community_site(self) -> Optional["CommunitySite"]:
        return self.community.main_site

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update(get_community_context(self.community))
        return context

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.setdefault("community", self.community)
        return context
