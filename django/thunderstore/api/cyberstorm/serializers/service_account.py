from rest_framework import serializers


class CreateServiceAccountSerializer(serializers.Serializer):
    nickname = serializers.CharField(max_length=32)
    team_name = serializers.CharField(read_only=True)
    api_token = serializers.CharField(read_only=True)


class DeleteServiceAccountSerializer(serializers.Serializer):
    uuid = serializers.UUIDField()
