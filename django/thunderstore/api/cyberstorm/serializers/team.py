from rest_framework import serializers

# from api.serializers import CyberstormDynamicLinksSerializer


class CyberstormTeamMemberSerializer(serializers.Serializer):

    user = serializers.CharField()
    # imageSource = serializers.CharField()
    role = serializers.CharField()

class CyberstormTeamSerializer(serializers.Serializer):

    name = serializers.CharField()
    # imageSource = serializers.CharField()
    # description = serializers.CharField()
    # about = serializers.CharField()
    members = CyberstormTeamMemberSerializer(many=True)
    # dynamicLinks = CyberstormDynamicLinksSerializer(many=True)
    donationLink = serializers.CharField()
