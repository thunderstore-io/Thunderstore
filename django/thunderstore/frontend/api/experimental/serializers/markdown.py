from rest_framework import serializers


class RenderMarkdownParamsSerializer(serializers.Serializer):
    markdown = serializers.CharField()


class RenderMarkdownResponseSerializer(serializers.Serializer):
    html = serializers.CharField()
