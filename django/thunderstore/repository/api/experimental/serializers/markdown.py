from rest_framework import serializers


class MarkdownResponseSerializer(serializers.Serializer):
    markdown = serializers.CharField(required=True, allow_null=True)
