from django.http import Http404
from django.utils.cache import patch_cache_control
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.moderation.pagination import MarkdownHistoryPagination
from thunderstore.moderation.permissions import (
    CanViewMarkdownRevisions,
    ensure_user_can_view_markdown_history,
)
from thunderstore.moderation.serializers import (
    MarkdownChangeSerializer,
    MarkdownChangesQuerySerializer,
    MarkdownRevisionSerializer,
    OriginalMarkdownSerializer,
)
from thunderstore.repository.consts import MARKDOWN_FIELDS, MarkdownDocument
from thunderstore.repository.models import (
    PackageVersion,
    PackageVersionMarkdownRevision,
)


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


class MarkdownChangesAPIView(APIView):
    """
    README and CHANGELOG revisions in ascending ID order, including resets and
    inactive packages. Pass the returned cursor as `after` on the next request,
    even when has_more is false, and only store it once the page is processed.
    """

    permission_classes = [IsAuthenticated, CanViewMarkdownRevisions]
    swagger_schema = None
    page_size = 10

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        patch_cache_control(response, private=True, no_store=True)
        return response

    def get(self, request):
        params = MarkdownChangesQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        after = params.validated_data["after"]
        revisions = list(
            PackageVersionMarkdownRevision.objects.filter(id__gt=after)
            .select_related("version__package", "edited_by")
            .defer(
                "version__readme",
                "version__changelog",
                "version__readme_override",
                "version__changelog_override",
            )
            .order_by("id")[: self.page_size + 1]
        )
        page = revisions[: self.page_size]
        return Response(
            {
                "results": MarkdownChangeSerializer(page, many=True).data,
                "cursor": page[-1].pk if page else after,
                "has_more": len(revisions) > self.page_size,
            }
        )
