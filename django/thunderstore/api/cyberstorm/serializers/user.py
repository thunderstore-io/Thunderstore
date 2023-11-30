from rest_framework import serializers


class CyberstormAccountDeleteRequestSerialiazer(serializers.Serializer):
    verification = serializers.CharField()


class CyberstormAccountDeleteResponseSerialiazer(serializers.Serializer):
    user = serializers.CharField()
