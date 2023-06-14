from django.db.models import Count, Sum
from django.http import Http404, HttpRequest, HttpResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from thunderstore.repository.models.team import Team

from thunderstore.api.cyberstorm.serializers import CyberstormTeamSerializer, CyberstormTeamMemberSerializer


class TeamAPIView(APIView):
    permission_classes = []

    @swagger_auto_schema(
        responses={200: CyberstormTeamSerializer()},
        operation_id="api.team",
    )
    def get(self, request: HttpRequest, team_identifier: str) -> HttpResponse:
        try:
            t = Team.objects.get(
                name=team_identifier,
            )
        except Team.DoesNotExist:
            raise Http404(f"Coudln't find team with the identifier {team_identifier}")
        
        serializer = self.serialize_results(t)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def serialize_results(self, team: Team):
        return CyberstormTeamSerializer(
            {
                "name": team.name,
                "members": [
                    CyberstormTeamMemberSerializer({"user": team_member.user.username, "role": team_member.role}).data
                    for team_member in team.members.all()
                ],
                "donationLink": team.donation_link,
            }
        )