from rest_framework.generics import RetrieveAPIView

from thunderstore.api.cyberstorm.serializers import CyberstormTeamSerializer
from thunderstore.repository.models.team import Team


class TeamDetailAPIView(RetrieveAPIView):
    permission_classes = []
    serializer_class = CyberstormTeamSerializer
    queryset = Team.objects.exclude(is_active=False).prefetch_related("members")
    lookup_field = "name"
    lookup_url_kwarg = "team_id"
