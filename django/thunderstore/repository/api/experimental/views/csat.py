from random import random
from uuid import uuid4

from django.conf import settings
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.repository.api.experimental.serializers import (
    AnalyticsEventCsatSurveyResponse,
    CsatStatusResponseSerializer,
    CsatSubmitRequestSerializer,
)
from thunderstore.ts_analytics.kafka import KafkaTopic
from thunderstore.ts_analytics.tasks import send_kafka_message


@method_decorator(never_cache, name="dispatch")
class CsatStatusApiView(APIView):
    """
    Get if the CSAT survey is enabled and if it should be made visible
    in the client.
    """

    authentication_classes = []
    permission_classes = []

    @swagger_auto_schema(auto_schema=None)
    def get(self, request, *args, **kwargs):
        if not settings.CSAT_SURVEY_ENABLED:
            return Response(
                CsatStatusResponseSerializer(
                    instance={"enabled": False, "eligible": False}
                ).data
            )

        # CSAT surveys are only shown after (a) client conditions are correct
        # and (b) after some random dice roll. This is mainly just to control
        # the volume of submissions and is meant to be tuneable.
        eligible = random() < settings.CSAT_SURVEY_ELIGIBLE_CHANCE
        return Response(
            CsatStatusResponseSerializer(
                instance={"enabled": True, "eligible": eligible}
            ).data
        )


class CsatSubmitApiView(APIView):
    """
    Submit a CSAT survey response.
    """

    authentication_classes = []
    permission_classes = []

    @swagger_auto_schema(auto_schema=None)
    def post(self, request, *args, **kwargs):
        if not settings.CSAT_SURVEY_ENABLED:
            return Response(status=status.HTTP_503_SERVICE_UNAVAILABLE)

        serializer = CsatSubmitRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        payload = AnalyticsEventCsatSurveyResponse(
            id=str(uuid4()),
            timestamp=timezone.now(),
            score=data["score"],
            comment=data.get("comment") or "",
            app_version=data["app_version"],
        )
        send_kafka_message.delay(
            topic=KafkaTopic.A_CSAT_SURVEY_RESPONSE_V1,
            payload_string=payload.json(),
        )

        return Response({}, status=status.HTTP_200_OK)
