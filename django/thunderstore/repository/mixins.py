class CommunityMixin:
    @property
    def community_identifier(self):
        return self.kwargs["community_identifier"]

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["community_identifier"] = self.community_identifier
        return context
