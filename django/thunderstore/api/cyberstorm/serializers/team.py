from typing import Optional

from django.core.validators import URLValidator
from rest_framework import serializers

from thunderstore.repository.forms import AddTeamMemberForm
from thunderstore.repository.validators import PackageReferenceComponentValidator
from thunderstore.social.utils import get_user_avatar_url


class CyberstormTeamSerializer(serializers.Serializer):
    """
    This is for team's public profile and readably by anyone. Don't add
    any sensitive information here.
    """

    identifier = serializers.IntegerField(source="id")
    name = serializers.CharField()
    donation_link = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )


class CyberstormTeamMemberSerializer(serializers.Serializer):
    identifier = serializers.IntegerField(source="user.id")
    username = serializers.CharField(source="user.username")
    avatar = serializers.SerializerMethodField(allow_null=True)
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


class CyberstormTeamUpdateSerializer(serializers.Serializer):
    donation_link = serializers.CharField(
        max_length=1024, validators=[URLValidator(["https"])]
    )
