class CommunityMixin:
    @property
    def community_identifier(self):
        return (
            self.kwargs.get("community_identifier", None)
            or self.request.community.identifier
        )
