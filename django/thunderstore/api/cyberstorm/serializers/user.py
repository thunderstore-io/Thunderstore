from rest_framework import serializers


class CyberstormUserSerializer(serializers.Serializer):
    identifier = serializers.CharField(source="id")
    username = serializers.CharField()
