from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.api.cyberstorm.serializers import (
    CommunityPermissionsSerializer,
    CyberstormCommunityDetailSerializer,
)
from thunderstore.api.utils import (
    CyberstormAutoSchemaMixin,
    PublicCacheMixin,
    conditional_swagger_auto_schema,
)
from thunderstore.community.models import Community, ModeratorNote


class CommunityAPIView(PublicCacheMixin, CyberstormAutoSchemaMixin, RetrieveAPIView):
    lookup_url_kwarg = "community_id"
    lookup_field = "identifier"
    permission_classes = []

    # Unlisted communities are included, as direct links to them should work.
    queryset = Community.objects.prefetch_related(
        Prefetch(
            "moderator_notes",
            queryset=ModeratorNote.objects.filter(is_active=True),
        )
    )
    serializer_class = CyberstormCommunityDetailSerializer

    def get_object(self):
        community = super().get_object()
        # All active community notes (read from the prefetched active-only set).
        community.display_moderator_notes = list(community.moderator_notes.all())
        return community

    def get(self, *args, **kwargs):
        response = super().get(*args, **kwargs)
        return response


class CommunityPermissionsAPIView(APIView):
    """The current user's community-level permissions, used to gate moderator UI."""

    permission_classes = [IsAuthenticated]

    @conditional_swagger_auto_schema(
        operation_id="cyberstorm.community.permissions",
        responses={200: CommunityPermissionsSerializer},
        tags=["cyberstorm"],
    )
    def get(self, request, *args, **kwargs) -> Response:
        community = get_object_or_404(Community, identifier=kwargs["community_id"])
        data = {
            "permissions": {
                "can_moderate": community.can_user_manage_packages(request.user),
            },
        }
        serializer = CommunityPermissionsSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)
