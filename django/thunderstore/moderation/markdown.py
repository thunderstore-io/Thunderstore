from django.utils.cache import patch_cache_control
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.moderation.markdown_history import MarkdownRevisionSerializer
from thunderstore.moderation.permissions import CanViewMarkdownRevisions
from thunderstore.repository.models import PackageVersionMarkdownRevision


class MarkdownChangesQuerySerializer(serializers.Serializer):
    after = serializers.IntegerField(default=0, min_value=0, max_value=2**63 - 1)


class MarkdownChangeSerializer(MarkdownRevisionSerializer):
    version_id = serializers.IntegerField()
    namespace = serializers.CharField(source="version.package.namespace_id")
    package_name = serializers.CharField(source="version.package.name")
    version_number = serializers.CharField(source="version.version_number")
    editor_username = serializers.CharField(
        source="edited_by.username", allow_null=True
    )

    class Meta(MarkdownRevisionSerializer.Meta):
        fields = MarkdownRevisionSerializer.Meta.fields + (
            "version_id",
            "namespace",
            "package_name",
            "version_number",
            "document",
            "editor_username",
        )
        read_only_fields = fields


class MarkdownChangesResponseSerializer(serializers.Serializer):
    results = MarkdownChangeSerializer(many=True)
    cursor = serializers.IntegerField()
    has_more = serializers.BooleanField()


class MarkdownChangesAPIView(APIView):
    permission_classes = [IsAuthenticated, CanViewMarkdownRevisions]
    page_size = 10

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        patch_cache_control(response, private=True, no_store=True)
        return response

    @swagger_auto_schema(
        query_serializer=MarkdownChangesQuerySerializer,
        responses={200: MarkdownChangesResponseSerializer},
        operation_description=(
            "Poll saved README and CHANGELOG revisions in ascending ID order. "
            "Pass the returned cursor as after on the next request, including "
            "when has_more is false. Checkpoint only after processing the page. "
            "Includes resets and revisions of inactive packages and versions."
        ),
        tags=["moderation"],
    )
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
