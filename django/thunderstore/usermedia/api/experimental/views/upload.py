from datetime import timedelta

from botocore.exceptions import ClientError
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from thunderstore.usermedia.api.experimental.serializers import (
    UserMediaCreatePartUploadUrlsParams,
    UserMediaFinishUploadParamsSerializer,
    UserMediaInitiateUploadParams,
    UserMediaSerializer,
    UserMediaUploadUrlsSerializer,
)
from thunderstore.usermedia.exceptions import InvalidUploadStateException
from thunderstore.usermedia.models import UserMedia
from thunderstore.usermedia.s3_client import get_s3_client
from thunderstore.usermedia.s3_upload import (
    abort_upload,
    create_upload,
    finalize_upload,
    get_signed_upload_urls,
)

PART_SIZE = 1024 * 1024 * 50


class UserMediaInitiateUploadApiView(GenericAPIView):
    queryset = UserMedia.objects.active()
    serializer_class = UserMediaSerializer
    # TODO: Add test for permission check
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=UserMediaInitiateUploadParams,
        responses={201: UserMediaSerializer()},
        operation_id="experimental.usermedia.initiate-upload",
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

        total_size = validator.validated_data["file_size_bytes"]
        part_count = -(-total_size // PART_SIZE)

        try:
            upload_urls = get_signed_upload_urls(
                user=request.user,
                client=get_s3_client(for_signing=True),
                user_media=instance,
                part_count=part_count,
                total_size=total_size,
            )
        except InvalidUploadStateException as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
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

        try:
            finalize_upload(
                user=request.user,
                client=client,
                user_media=instance,
                parts=validator.validated_data["parts"],
            )
        except InvalidUploadStateException as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
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
    # TODO: Add test for permission check
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={200: UserMediaSerializer()},
        operation_id="experimental.usermedia.abort-upload",
    )
    def post(self, request, *args, **kwargs):
        instance = self.get_object()
        client = get_s3_client()
        try:
            abort_upload(request.user, client, instance)
        except ClientError as e:
            if e.__class__.__name__ == "NoSuchUpload":
                return Response(
                    {"error": "Upload not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            else:
                raise
        except InvalidUploadStateException as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = UserMediaSerializer(instance)
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
