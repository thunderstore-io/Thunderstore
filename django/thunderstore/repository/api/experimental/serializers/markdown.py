from rest_framework import serializers


class MarkdownResponseSerializer(serializers.Serializer):
    markdown = serializers.CharField(required=True, allow_null=True)
    is_edited = serializers.BooleanField(default=False)
    edited_at = serializers.DateTimeField(allow_null=True, default=None)
