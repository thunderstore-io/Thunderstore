from datetime import timedelta

from django.utils import timezone
from drf_yasg.utils import no_body, swagger_auto_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from thunderstore.usermedia.api.experimental.serializers import (
    UserMediaCreatePartUploadUrlsParams,
    UserMediaSerializer,
    UserMediaUploadUrlsSerializer,
)
from thunderstore.usermedia.api.experimental.serializers.upload import (
    UserMediaFinishUploadParamsSerializer,
)
from thunderstore.usermedia.models import UserMedia
from thunderstore.usermedia.s3_client import get_s3_client
from thunderstore.usermedia.s3_upload import (
    create_upload,
    finalize_upload,
    get_signed_upload_urls,
)

PART_SIZE = 1024 * 1024 * 6


class UserMediaInitiateUploadApiView(GenericAPIView):
    queryset = UserMedia.objects.active()
    serializer_class = UserMediaSerializer
    # TODO: Add test for permission check
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=no_body,
        responses={201: UserMediaSerializer()},
        operation_id="experimental.usermedia.initiate-upload",
    )
    def post(self, request, *args, **kwargs):
        client = get_s3_client()
        user_media = create_upload(
            client=client, user=request.user, expiry=timezone.now() + timedelta(days=1)
        )
        serializer = self.get_serializer(user_media)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )


class UserMediaCreatePartUploadUrlsApiView(GenericAPIView):
    queryset = UserMedia.objects.active()
    lookup_field = "uuid"
    lookup_url_kwarg = "uuid"
    serializer_class = UserMediaCreatePartUploadUrlsParams
    # TODO: Add test for permission check
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=UserMediaCreatePartUploadUrlsParams,
        responses={200: UserMediaUploadUrlsSerializer()},
        operation_id="experimental.usermedia.create-part-upload-urls",
    )
    def post(self, request, *args, **kwargs):
        instance = self.get_object()

        validator = self.get_serializer(data=request.data)
        validator.is_valid(raise_exception=True)

        part_count = -(-validator.data["file_size_bytes"] // PART_SIZE)

        upload_urls = get_signed_upload_urls(
            user=request.user,
            client=get_s3_client(for_signing=True),
            user_media=instance,
            part_count=part_count,
        )
        serializer = UserMediaUploadUrlsSerializer(
            {
                "upload_urls": upload_urls,
                "part_size": PART_SIZE,
            }
        )
        return Response(serializer.data)


class UserMediaFinishUploadApiView(GenericAPIView):
    queryset = UserMedia.objects.active()
    lookup_field = "uuid"
    lookup_url_kwarg = "uuid"
    serializer_class = UserMediaFinishUploadParamsSerializer
    # TODO: Add test for permission check
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=UserMediaFinishUploadParamsSerializer(),
        responses={200: UserMediaSerializer()},
        operation_id="experimental.usermedia.finish-upload",
    )
    def post(self, request, *args, **kwargs):
        instance = self.get_object()
        client = get_s3_client()

        validator = self.get_serializer(data=request.data)
        validator.is_valid(raise_exception=True)

        finalize_upload(
            user=request.user,
            client=client,
            user_media=instance,
            parts=validator.data["parts"],
        )
        serializer = UserMediaSerializer(instance)
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
