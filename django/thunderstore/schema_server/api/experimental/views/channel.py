from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.utils.cache import get_conditional_response
from django.utils.http import http_date
from drf_yasg.openapi import TYPE_FILE, Schema
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.ipfs.models import IPFSObject
from thunderstore.schema_server.models import SchemaChannel


class SchemaChannelUpdateResponseSerializer(serializers.Serializer):
    channel_identifier = serializers.CharField(required=True)
    checksum_sha256 = serializers.CharField(required=True)


# We need to override the get_filename function since DRF for some reason
# explicitly requires a filename, which we don't really care about
class SchemaFileUploadParser(FileUploadParser):
    def get_filename(self, stream, media_type, parser_context):
        return f"upload-{timezone.now().timestamp()}.bin"


class SchemaChannelApiView(APIView):
    permission_classes = []
    parser_classes = [SchemaFileUploadParser]
    throttle_classes = []

    @swagger_auto_schema(
        request_body=Schema(title="content", type=TYPE_FILE),
        responses={200: SchemaChannelUpdateResponseSerializer()},
        operation_id="experimental.schema.channel.update",
    )
    def post(self, request, channel: str, *args, **kwargs):
        if "file" not in self.request.data or not self.request.data["file"]:
            raise ValidationError(detail="Request body was empty")

        stream = self.request.data["file"].open()
        content = stream.read()

        try:
            result = SchemaChannel.update_channel(self.request.user, channel, content)
        except DjangoPermissionDenied:
            raise PermissionDenied()
        except SchemaChannel.DoesNotExist:
            raise NotFound()

        serializer = SchemaChannelUpdateResponseSerializer(
            {
                "channel_identifier": result.channel.identifier,
                "checksum_sha256": result.file.checksum_sha256,
            }
        )
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    @swagger_auto_schema(
        responses={200: Schema(title="content", type=TYPE_FILE)},
        operation_id="experimental.schema.channel.retrieve",
    )
    def get(self, request, channel: str, *args, **kwargs):
        channel = get_object_or_404(SchemaChannel, identifier=channel)
        if not channel.latest:
            raise NotFound()

        # TODO: Redirect to the IPFS gateway rather than returning data here
        ipfs_obj: IPFSObject = channel.latest.ipfs_object
        last_modified = int(ipfs_obj.datetime_created.timestamp())

        # TODO: Add ETag support if useful
        # Check if we can return a 304 response, otherwise return full content
        response = get_conditional_response(request, last_modified=last_modified)
        if response is None:
            response = HttpResponseRedirect(redirect_to=ipfs_obj.data.url)
            response["Last-Modified"] = http_date(last_modified)
        return response
