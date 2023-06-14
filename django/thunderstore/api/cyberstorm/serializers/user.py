from rest_framework import serializers

# from api.serializers import CyberstormDynamicLinksSerializer


# class CyberstormBadgeAchievementSerializer(serializers.Serializer):
#     name = serializers.CharField()
#     description = serializers.CharField()
#     imageSource = serializers.CharField()
#     enabled = serializers.BooleanField()

class CyberstormUserSerializer(serializers.Serializer):
    name = serializers.CharField()
    # imageSource = serializers.CharField()
    # description = serializers.CharField()
    # about = serializers.CharField()
    accountCreated = serializers.DateTimeField()
    lastActive = serializers.DateTimeField()
    # dynamicLinks = CyberstormDynamicLinksSerializer(many=True)
    # achievements = CyberstormBadgeAchievementSerializer(many=True)
    # showAchievementsOnProfile = serializers.BooleanField()
    # badges = CyberstormBadgeAchievementSerializer(many=True)
    # showBadgesOnProfile = serializers.BooleanField()
