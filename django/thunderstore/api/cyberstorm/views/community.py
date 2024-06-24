from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny

from thunderstore.api.cyberstorm.serializers import CyberstormCommunitySerializer
from thunderstore.api.utils import CyberstormAutoSchemaMixin
from thunderstore.community.models import Community


class CommunityAPIView(CyberstormAutoSchemaMixin, RetrieveAPIView):
    lookup_url_kwarg = "community_id"
    lookup_field = "identifier"
    permission_classes = [AllowAny]

    # Unlisted communities are included, as direct links to them should work.
    queryset = Community.objects.all()
    serializer_class = CyberstormCommunitySerializer
