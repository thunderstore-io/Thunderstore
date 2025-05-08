from typing import Optional

from rest_framework import serializers

from thunderstore.repository.forms import AddTeamMemberForm
from thunderstore.repository.models.team import TeamMemberRole
from thunderstore.repository.validators import PackageReferenceComponentValidator
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


class CyberstormTeamAddMemberRequestSerializer(serializers.Serializer):
    username = serializers.CharField()
    role = serializers.ChoiceField(
        choices=AddTeamMemberForm.base_fields["role"].choices
    )


class CyberstormTeamAddMemberResponseSerializer(serializers.Serializer):
    username = serializers.CharField(source="user")
    role = serializers.CharField()
    team = serializers.CharField()


class CyberstormCreateTeamSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=64, validators=[PackageReferenceComponentValidator("Author name")]
    )


class CyberstormTeamMemberUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=TeamMemberRole.as_choices())
    team_name = serializers.CharField(source="team.name", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
