from django.http import Http404
from django.utils.cache import patch_cache_control
from rest_framework import serializers, status
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.api.cyberstorm.services.package_version import (
    ensure_user_can_view_markdown_history,
)
from thunderstore.api.utils import conditional_swagger_auto_schema
from thunderstore.repository.models import (
    PackageVersion,
    PackageVersionMarkdownRevision,
)


class MarkdownRevisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageVersionMarkdownRevision
        fields = (
            "id",
            "content",
            "is_override",
            "recorded_at",
            "edited_at",
            "edited_by",
        )
        read_only_fields = fields


class OriginalMarkdownSerializer(serializers.Serializer):
    content = serializers.CharField(allow_blank=True, allow_null=True)
    uploaded_at = serializers.DateTimeField()
    uploaded_by = serializers.IntegerField(allow_null=True)


class MarkdownHistoryResponseSerializer(serializers.Serializer):
    original = OriginalMarkdownSerializer()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = MarkdownRevisionSerializer(many=True)


class MarkdownHistoryPagination(CursorPagination):
    page_size = 10
    ordering = "-id"


class PackageVersionMarkdownHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        patch_cache_control(response, private=True, no_store=True)
        return response

    @conditional_swagger_auto_schema(
        operation_id="cyberstorm.package.version.markdown.history",
        responses={status.HTTP_200_OK: MarkdownHistoryResponseSerializer},
        tags=["cyberstorm"],
    )
    def get(
        self,
        request,
        namespace_id: str,
        package_name: str,
        version_number: str,
        document: str,
    ) -> Response:
        if document not in PackageVersionMarkdownRevision.Document.values:
            raise Http404

        # Removed versions remain available for moderation.
        version = get_object_or_404(
            PackageVersion.objects.select_related("package"),
            package__namespace__name=namespace_id,
            package__name=package_name,
            version_number=version_number,
        )
        ensure_user_can_view_markdown_history(request.user, version)

        paginator = MarkdownHistoryPagination()
        page = paginator.paginate_queryset(
            version.markdown_revisions.filter(document=document), request, view=self
        )
        response = paginator.get_paginated_response(
            MarkdownRevisionSerializer(page, many=True).data
        )
        response.data["original"] = OriginalMarkdownSerializer(
            {
                "content": getattr(version, document),
                "uploaded_at": version.date_created,
                "uploaded_by": version.uploaded_by_id,
            }
        ).data
        return response
