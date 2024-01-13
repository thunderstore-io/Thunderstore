from django.http import HttpResponse
from django.shortcuts import redirect
from drf_yasg.openapi import TYPE_FILE, Schema
from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from thunderstore.modpacks.api.experimental.serializers.serializers import LegacyProfileMetaDataSerializer

from thunderstore.modpacks.models import LegacyProfileMetaData


class LegacyProfileMetaDataRetrieveApiView(APIView):
    permission_classes = []

    @swagger_auto_schema(
        responses={200: LegacyProfileMetaDataSerializer()},
        operation_id="experimental.modpacks.legacyprofilemetadata.retrieve",
    )
    def get(self, request, key: str, *args, **kwargs) -> HttpResponse:
        obj = LegacyProfileMetaData.objects.filter(profile__id=key).last()
        serializer = LegacyProfileMetaDataSerializer({"code": obj.profile_meta_data["code"], "name": obj.profile_meta_data["name"], "mods": obj.profile_meta_data["mods"], "game": obj.profile_meta_data["game"], "game_display_name": obj.profile_meta_data["game_display_name"]})
        return Response(serializer.data, status=status.HTTP_200_OK)
