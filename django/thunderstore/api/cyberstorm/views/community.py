from rest_framework.generics import RetrieveAPIView

from thunderstore.api.cyberstorm.serializers import CyberstormCommunitySerializer
from thunderstore.api.utils import CyberstormAutoSchemaMixin
from thunderstore.community.models import Community


class CommunityAPIView(CyberstormAutoSchemaMixin, RetrieveAPIView):
    lookup_url_kwarg = "community_id"
    lookup_field = "identifier"
    permission_classes = []

    # Unlisted communities are included, as direct links to them should work.
    queryset = Community.objects.all()
    serializer_class = CyberstormCommunitySerializer

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "public, max-age=60"
        return response
