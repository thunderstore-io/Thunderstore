from typing import Optional

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from thunderstore.repository.forms import AddTeamMemberForm
from thunderstore.repository.models import Namespace, Team
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


class CyberstormTeamAddMemberRequestSerialiazer(serializers.Serializer):
    username = serializers.CharField()
    role = serializers.ChoiceField(
        choices=AddTeamMemberForm.base_fields["role"].choices
    )


class CyberstormTeamAddMemberResponseSerialiazer(serializers.Serializer):
    username = serializers.CharField(source="user")
    role = serializers.CharField()
    team = serializers.CharField()


class CyberstormCreateTeamSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=64, validators=[PackageReferenceComponentValidator("Author name")]
    )

    def validate_name(self, value: str) -> str:
        if Team.objects.filter(name__iexact=value.lower()).exists():
            raise ValidationError("A team with the provided name already exists")
        if Namespace.objects.filter(name__iexact=value.lower()).exists():
            raise ValidationError("A namespace with the provided name already exists")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        user = self.context["request"].user
        if getattr(user, "service_account", None) is not None:
            raise ValidationError("Service accounts cannot create teams")
        return attrs
