from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny

from thunderstore.api.cyberstorm.serializers import CyberstormCommunitySerializer
from thunderstore.api.utils import conditional_swagger_auto_schema
from thunderstore.community.models import Community


class CommunityDetailAPIView(RetrieveAPIView):
    lookup_url_kwarg = "community_id"
    lookup_field = "identifier"
    permission_classes = [AllowAny]

    # Unlisted communities are included, as direct links to them should work.
    queryset = Community.objects.all()
    serializer_class = CyberstormCommunitySerializer

    @conditional_swagger_auto_schema(tags=["cyberstorm"])
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)
