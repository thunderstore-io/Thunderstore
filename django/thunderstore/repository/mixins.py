from thunderstore.community.models.community import Community


class CommunityMixin:
    @property
    def community_identifier(self):
        return (
            self.kwargs.get("community_identifier", None)
            or self.request.community.identifier
        )

    @property
    def solved_community_from_identifier(self):
        return Community.objects.get(identifier=self.community_identifier)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["community_identifier"] = self.community_identifier
        return context
