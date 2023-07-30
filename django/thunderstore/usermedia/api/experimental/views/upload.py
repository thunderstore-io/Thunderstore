from datetime import timedelta

from botocore.exceptions import ClientError
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from thunderstore.usermedia.api.experimental.serializers import (
    UserMediaFinishUploadParamsSerializer,
    UserMediaInitiateUploadParams,
    UserMediaInitiateUploadResponseSerializer,
    UserMediaSerializer,
)
from thunderstore.usermedia.models import UserMedia
from thunderstore.usermedia.s3_client import get_s3_client
from thunderstore.usermedia.s3_upload import (
    abort_upload,
    create_upload,
    finalize_upload,
    get_signed_upload_urls,
)


class UserMediaInitiateUploadApiView(GenericAPIView):
    queryset = UserMedia.objects.active()
    serializer_class = UserMediaInitiateUploadResponseSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=UserMediaInitiateUploadParams,
        responses={201: UserMediaInitiateUploadResponseSerializer()},
        operation_id="experimental.usermedia.initiate-upload",
        tags=["usermedia"],
    )
    def post(self, request, *args, **kwargs):
        validator = UserMediaInitiateUploadParams(data=request.data)
        validator.is_valid(raise_exception=True)
        total_size = validator.validated_data["file_size_bytes"]

        client = get_s3_client()
        user_media = create_upload(
            client=client,
            user=request.user,
            filename=validator.validated_data["filename"],
            size=total_size,
            expiry=timezone.now() + timedelta(days=1),
        )

        upload_urls = get_signed_upload_urls(
            user=request.user,
            client=get_s3_client(for_signing=True),
            user_media=user_media,
        )

        serializer = self.get_serializer(
            {
                "user_media": user_media,
                "upload_urls": upload_urls,
            },
        )
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )


class UserMediaFinishUploadApiView(GenericAPIView):
    queryset = UserMedia.objects.active()
    lookup_field = "uuid"
    lookup_url_kwarg = "uuid"
    serializer_class = UserMediaFinishUploadParamsSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=UserMediaFinishUploadParamsSerializer(),
        responses={200: UserMediaSerializer()},
        operation_id="experimental.usermedia.finish-upload",
        tags=["usermedia"],
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
            parts=validator.validated_data["parts"],
        )
        serializer = UserMediaSerializer(instance)
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class UserMediaAbortUploadApiView(GenericAPIView):
    queryset = UserMedia.objects.active()
    lookup_field = "uuid"
    lookup_url_kwarg = "uuid"
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={200: UserMediaSerializer()},
        operation_id="experimental.usermedia.abort-upload",
        tags=["usermedia"],
    )
    def post(self, request, *args, **kwargs):
        instance = self.get_object()
        client = get_s3_client()
        try:
            abort_upload(request.user, client, instance)
        except ClientError as e:
            if e.__class__.__name__ == "NoSuchUpload":
                return Response(
                    {"detail": "Upload not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            else:
                raise
        serializer = UserMediaSerializer(instance)
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
