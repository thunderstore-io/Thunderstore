from django.http import Http404, HttpResponse
from drf_yasg import openapi
from drf_yasg.inspectors import SwaggerAutoSchema
from rest_framework import serializers, status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from thunderstore.api.cyberstorm.services.package_version import (
    delete_markdown_override,
    update_markdown_override,
)
from thunderstore.api.utils import PublicCacheMixin, conditional_swagger_auto_schema
from thunderstore.repository.consts import MARKDOWN_FIELDS, MarkdownDocument
from thunderstore.repository.models import PackageVersion
from thunderstore.repository.validation.markdown import MAX_MARKDOWN_SIZE


class MarkdownOverrideThrottle(UserRateThrottle):
    scope = "markdown_override"

    def get_rate(self) -> str:
        return "20/h"


class UpdateMarkdownOverrideSerializer(serializers.Serializer):
    content = serializers.CharField(
        allow_blank=True,
        trim_whitespace=False,
        max_length=MAX_MARKDOWN_SIZE,
    )


class MarkdownOverrideStateSerializer(serializers.Serializer):
    is_edited = serializers.BooleanField()
    edited_at = serializers.DateTimeField(allow_null=True)


def get_active_version(
    namespace_id: str, package_name: str, version_number: str
) -> PackageVersion:
    return get_object_or_404(
        PackageVersion.objects.active(),
        package__namespace__name=namespace_id,
        package__name=package_name,
        package__is_active=True,
        version_number=version_number,
    )


def get_markdown_document(document: str) -> MarkdownDocument:
    if document not in MarkdownDocument.values:
        raise Http404
    return MarkdownDocument(document)


class PackageVersionMarkdownUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [MarkdownOverrideThrottle]

    @conditional_swagger_auto_schema(
        operation_id="cyberstorm.package.version.markdown.update",
        request_body=UpdateMarkdownOverrideSerializer,
        responses={status.HTTP_200_OK: MarkdownOverrideStateSerializer},
        tags=["cyberstorm"],
    )
    def patch(
        self,
        request,
        namespace_id: str,
        package_name: str,
        version_number: str,
        document: str,
    ) -> Response:
        document = get_markdown_document(document)
        serializer = UpdateMarkdownOverrideSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        version = get_active_version(namespace_id, package_name, version_number)
        version = update_markdown_override(
            agent=request.user,
            version=version,
            document=document,
            content=serializer.validated_data["content"],
        )

        fields = MARKDOWN_FIELDS[document]
        response_serializer = MarkdownOverrideStateSerializer(
            {
                "is_edited": getattr(version, fields.override) is not None,
                "edited_at": getattr(version, fields.edited_at),
            }
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class PackageVersionMarkdownDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [MarkdownOverrideThrottle]

    @conditional_swagger_auto_schema(
        operation_id="cyberstorm.package.version.markdown.delete",
        responses={status.HTTP_204_NO_CONTENT: ""},
        tags=["cyberstorm"],
    )
    def delete(
        self,
        request,
        namespace_id: str,
        package_name: str,
        version_number: str,
        document: str,
    ) -> Response:
        document = get_markdown_document(document)
        version = get_active_version(namespace_id, package_name, version_number)
        delete_markdown_override(
            agent=request.user,
            version=version,
            document=document,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class MarkdownDownloadSchema(SwaggerAutoSchema):
    def get_produces(self):
        return ["text/markdown"]


class PackageVersionMarkdownDownloadAPIView(PublicCacheMixin, APIView):
    """
    Download the raw markdown of an override.
    """

    swagger_schema = MarkdownDownloadSchema

    @conditional_swagger_auto_schema(
        responses={status.HTTP_200_OK: openapi.Schema(type=openapi.TYPE_STRING)},
        tags=["cyberstorm"],
    )
    def get(
        self,
        request,
        namespace_id: str,
        package_name: str,
        version_number: str,
        document: str,
    ) -> HttpResponse:
        version = get_active_version(namespace_id, package_name, version_number)
        fields = MARKDOWN_FIELDS[get_markdown_document(document)]

        content = getattr(version, fields.override)
        if content is None:
            raise Http404

        response = HttpResponse(content, content_type="text/markdown; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{fields.filename}"'
        return response
