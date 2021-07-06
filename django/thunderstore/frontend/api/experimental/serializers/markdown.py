from rest_framework import serializers

from thunderstore.repository.package_upload import MAX_README_SIZE


class RenderMarkdownParamsSerializer(serializers.Serializer):
    markdown = serializers.CharField(max_length=MAX_README_SIZE)


class RenderMarkdownResponseSerializer(serializers.Serializer):
    html = serializers.CharField()
