from django.http import HttpResponse
from drf_yasg.utils import swagger_auto_schema  # type: ignore
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_409_CONFLICT
from rest_framework.views import APIView

from thunderstore.ts_trending.api.experimental.parsers import GzipJSONParser
from thunderstore.ts_trending.api.experimental.serializers import (
    IngestRequestSerializer,
)
from thunderstore.ts_trending.exceptions import EmptyScoresError, StaleScoresError
from thunderstore.ts_trending.permissions import TrendingSharedSecretPermission
from thunderstore.ts_trending.services.score import replace_scores


class IngestApiView(APIView):
    """
    Receive trending scores pushed by the query service.
    """

    parser_classes = [GzipJSONParser]
    permission_classes = [TrendingSharedSecretPermission]

    @swagger_auto_schema(auto_schema=None)
    def post(self, request: Request) -> HttpResponse:
        request_data = IngestRequestSerializer(data=request.data)
        request_data.is_valid(raise_exception=True)
        data = request_data.validated_data

        try:
            stored = replace_scores(data["computed_at"], data["sorts"])
        except StaleScoresError as e:
            return Response({"detail": str(e)}, HTTP_409_CONFLICT)
        except EmptyScoresError as e:
            return Response({"detail": str(e)}, HTTP_400_BAD_REQUEST)

        return Response(stored)
