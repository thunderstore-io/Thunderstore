from typing import Optional

from rest_framework import serializers

from thunderstore.social.utils import get_user_avatar_url


class CyberstormTeamSerializer(serializers.Serializer):
    """
    This is for team's public profile and readably by anyone. Don't add
    any sensitive information here.
    """

    identifier = serializers.IntegerField(source="id")
    name = serializers.CharField()
    donation_link = serializers.CharField(required=False)


class CyberstormTeamMemberSerializer(serializers.Serializer):
    identifier = serializers.IntegerField(source="user.id")
    username = serializers.CharField(source="user.username")
    avatar = serializers.SerializerMethodField()
    role = serializers.CharField()

    def get_avatar(self, obj) -> Optional[str]:
        return get_user_avatar_url(obj.user)


class CyberstormServiceAccountSerializer(serializers.Serializer):
    identifier = serializers.CharField(source="uuid")
    name = serializers.CharField(source="user.first_name")
    last_used = serializers.DateTimeField()


class CyberstormTeamCreateSerialiazer(serializers.Serializer):
    team_name = serializers.CharField()


class CyberstormTeamAddMemberSerialiazer(serializers.Serializer):
    user = serializers.CharField()
    role = serializers.CharField()


class CyberstormRemoveTeamMemberRequestSerialiazer(serializers.Serializer):
    user = serializers.CharField()


class CyberstormRemoveTeamMemberResponseSerialiazer(serializers.Serializer):
    team = serializers.CharField()
    user = serializers.CharField()


class CyberstormEditTeamMemberRequestSerialiazer(serializers.Serializer):
    user = serializers.CharField()
    role = serializers.CharField()


class CyberstormEditTeamMemberResponseSerialiazer(serializers.Serializer):
    team = serializers.CharField()
    user = serializers.CharField()
    role = serializers.CharField()


class CyberstormEditServiceAccountSerialiazer(serializers.Serializer):
    nickname = serializers.CharField()
