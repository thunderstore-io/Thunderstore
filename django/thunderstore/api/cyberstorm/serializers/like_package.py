from rest_framework import serializers


class LikePackageSerializerCyberstorm(serializers.Serializer):
    state = serializers.CharField()
    score = serializers.IntegerField()
