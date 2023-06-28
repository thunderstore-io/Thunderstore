from django.db.models import QuerySet
from rest_framework.generics import RetrieveAPIView

from thunderstore.api.cyberstorm.serializers import TeamSerializerCyberstorm
from thunderstore.repository.models.team import Team


class TeamDetailAPIView(RetrieveAPIView):
    permission_classes = []
    serializer_class = TeamSerializerCyberstorm
    lookup_field = "name"

    def get_queryset(self) -> QuerySet[Team]:
        return Team.objects.filter(is_active=True).prefetch_related("members")
