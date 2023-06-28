from rest_framework import serializers


class CommunitySerializerCyberstorm(serializers.Serializer):
    name = serializers.CharField()
    identifier = serializers.CharField()
    download_count = serializers.IntegerField(min_value=0, default=0)
    package_count = serializers.IntegerField(min_value=0, default=0)
    background_image_url = serializers.CharField()
    description = serializers.CharField()
    discord_link = serializers.CharField(required=False)


class CommunityListQueryParameterSerializerCyberstorm(serializers.Serializer):
    page_size = serializers.IntegerField(default=50, min_value=1, max_value=50)
    ordering = serializers.ChoiceField(required=False, choices=["name"])
    page = serializers.IntegerField(default=1, min_value=1)


class CommunityListSerializerCyberstorm(serializers.Serializer):
    current = serializers.IntegerField()
    final = serializers.IntegerField()
    total = serializers.IntegerField()
    count = serializers.IntegerField()
    results = CommunitySerializerCyberstorm(many=True)
