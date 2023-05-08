from rest_framework import serializers


class LegacyProfileMetaDataSerializer(serializers.Serializer):
    code = serializers.CharField()
    mods = serializers.ListField()
    name = serializers.CharField()
    game = serializers.CharField()
    game_display_name = serializers.CharField()
