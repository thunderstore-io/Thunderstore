from rest_framework import serializers


class CyberstormCommunitySerializer(serializers.Serializer):

    name = serializers.CharField()
    namespace = serializers.CharField()
    downloadCount = serializers.IntegerField()
    packageCount = serializers.IntegerField()
    imageSource = serializers.CharField()
    serverCount = serializers.IntegerField()
    description = serializers.CharField()
    discordLink = serializers.CharField()
