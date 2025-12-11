from rest_framework.generics import RetrieveAPIView

from thunderstore.api.cyberstorm.serializers import CyberstormCommunitySerializer
from thunderstore.api.utils import CyberstormAutoSchemaMixin, CyberstormTimedCacheMixin
from thunderstore.community.models import Community


class CommunityAPIView(CyberstormTimedCacheMixin, CyberstormAutoSchemaMixin, RetrieveAPIView):
    lookup_url_kwarg = "community_id"
    lookup_field = "identifier"
    permission_classes = []

    # Unlisted communities are included, as direct links to them should work.
    queryset = Community.objects.all()
    serializer_class = CyberstormCommunitySerializer

    def get(self, *args, **kwargs):
        response = super().get(*args, **kwargs)
        return response
