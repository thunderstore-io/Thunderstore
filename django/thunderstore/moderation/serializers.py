from rest_framework import serializers

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
