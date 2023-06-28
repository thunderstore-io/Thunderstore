from rest_framework import serializers


class TeamMemberSerializerCyberstorm(serializers.Serializer):
    username = serializers.SerializerMethodField()
    role = serializers.CharField()

    def get_username(self, obj):
        return obj.user.username


class TeamSerializerCyberstorm(serializers.Serializer):
    identifier = serializers.SerializerMethodField()
    name = serializers.CharField()
    members = TeamMemberSerializerCyberstorm(many=True)
    donation_link = serializers.CharField()

    def get_identifier(
        self, obj
    ):  # Actually the name for now, until team names become editable
        return obj.name
