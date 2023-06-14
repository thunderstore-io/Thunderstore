from rest_framework import serializers

class CyberstormDynamicLinksSerializer(serializers.Serializer):
    title = serializers.CharField()
    url = serializers.CharField()