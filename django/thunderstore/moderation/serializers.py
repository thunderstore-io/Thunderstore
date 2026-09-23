from rest_framework import serializers

from thunderstore.moderation.pagination import MAX_CURSOR_ID
from thunderstore.repository.models import PackageVersionMarkdownRevision


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


class MarkdownChangesQuerySerializer(serializers.Serializer):
    after = serializers.IntegerField(default=0, min_value=0, max_value=MAX_CURSOR_ID)


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
