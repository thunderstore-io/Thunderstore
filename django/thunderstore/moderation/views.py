from django.http import Http404
from django.utils.cache import patch_cache_control
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.moderation.pagination import MarkdownHistoryPagination
from thunderstore.moderation.permissions import ensure_user_can_view_markdown_history
from thunderstore.moderation.serializers import (
    MarkdownRevisionSerializer,
    OriginalMarkdownSerializer,
)
from thunderstore.repository.consts import MARKDOWN_FIELDS, MarkdownDocument
from thunderstore.repository.models import PackageVersion


class PackageVersionMarkdownHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]
    swagger_schema = None

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        patch_cache_control(response, private=True, no_store=True)
        return response

    def get(
        self,
        request,
        namespace_id: str,
        package_name: str,
        version_number: str,
        document: str,
    ) -> Response:
        if document not in MarkdownDocument.values:
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
                "content": getattr(version, MARKDOWN_FIELDS[document].original),
                "uploaded_at": version.date_created,
                "uploaded_by": version.uploaded_by_id,
            }
        ).data
        return response
