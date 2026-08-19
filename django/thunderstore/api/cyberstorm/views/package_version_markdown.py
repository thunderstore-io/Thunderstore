from django.http import Http404, HttpResponse
from rest_framework import serializers, status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from thunderstore.api.cyberstorm.services.package_version import (
    update_markdown_overrides,
)
from thunderstore.api.utils import PublicCacheMixin, conditional_swagger_auto_schema
from thunderstore.markdown.templatetags.markdownify import render_markdown
from thunderstore.repository.models import PackageVersion
from thunderstore.repository.validation.markdown import MAX_MARKDOWN_SIZE


class MarkdownOverrideThrottle(UserRateThrottle):
    scope = "markdown_override"

    def get_rate(self) -> str:
        return "20/h"


class UpdateMarkdownOverridesSerializer(serializers.Serializer):
    readme = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=MAX_MARKDOWN_SIZE,
    )
    changelog = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=MAX_MARKDOWN_SIZE,
    )


class MarkdownOverrideStateSerializer(serializers.Serializer):
    html = serializers.CharField(allow_null=True)
    is_edited = serializers.BooleanField()
    edited_at = serializers.DateTimeField(allow_null=True)


class MarkdownOverridesResponseSerializer(serializers.Serializer):
    readme = MarkdownOverrideStateSerializer()
    changelog = MarkdownOverrideStateSerializer()


def get_active_version(
    namespace_id: str, package_name: str, version_number: str
) -> PackageVersion:
    return get_object_or_404(
        PackageVersion.objects.active().select_related("package", "package__owner"),
        package__namespace__name=namespace_id,
        package__name=package_name,
        version_number=version_number,
    )


def serialize_override_state(version: PackageVersion) -> dict:
    changelog = version.resolved_changelog
    return {
        "readme": {
            "html": render_markdown(version.resolved_readme),
            "is_edited": version.is_readme_edited,
            "edited_at": version.readme_override_edited_at,
        },
        "changelog": {
            "html": render_markdown(changelog) if changelog is not None else None,
            "is_edited": version.is_changelog_edited,
            "edited_at": version.changelog_override_edited_at,
        },
    }


class PackageVersionMarkdownAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [MarkdownOverrideThrottle]

    @conditional_swagger_auto_schema(
        operation_id="cyberstorm.package.version.markdown",
        request_body=UpdateMarkdownOverridesSerializer,
        responses={status.HTTP_200_OK: MarkdownOverridesResponseSerializer},
        tags=["cyberstorm"],
    )
    def post(
        self,
        request,
        namespace_id: str,
        package_name: str,
        version_number: str,
    ) -> Response:
        serializer = UpdateMarkdownOverridesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        version = get_active_version(namespace_id, package_name, version_number)
        version = update_markdown_overrides(
            agent=request.user,
            version=version,
            overrides=serializer.validated_data,
        )

        response_serializer = MarkdownOverridesResponseSerializer(
            serialize_override_state(version)
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class PackageVersionMarkdownDownloadAPIView(PublicCacheMixin, APIView):
    """
    Download the raw markdown of an override.
    """

    def get(
        self,
        request,
        namespace_id: str,
        package_name: str,
        version_number: str,
        document: str,
    ) -> HttpResponse:
        version = get_active_version(namespace_id, package_name, version_number)

        if document == "readme":
            content, filename = version.readme_override, "README.md"
        elif document == "changelog":
            content, filename = version.changelog_override, "CHANGELOG.md"
        else:
            raise Http404

        if content is None:
            raise Http404

        response = HttpResponse(content, content_type="text/markdown; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
