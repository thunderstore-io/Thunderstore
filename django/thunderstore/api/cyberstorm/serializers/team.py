from rest_framework import serializers

from .user import CyberstormUserSerializer


class CyberstormTeamMemberSerializer(serializers.Serializer):
    user = CyberstormUserSerializer()
    role = serializers.CharField()


class CyberstormTeamSerializer(serializers.Serializer):
    identifier = serializers.CharField(source="id")
    name = serializers.CharField()
    members = CyberstormTeamMemberSerializer(many=True)
    donation_link = serializers.CharField(required=False)
