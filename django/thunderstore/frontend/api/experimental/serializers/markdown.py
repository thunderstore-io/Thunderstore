from rest_framework import serializers

from thunderstore.repository.validation.markdown import MAX_MARKDOWN_SIZE


class RenderMarkdownParamsSerializer(serializers.Serializer):
    markdown = serializers.CharField(max_length=MAX_MARKDOWN_SIZE)


class RenderMarkdownResponseSerializer(serializers.Serializer):
    html = serializers.CharField()
