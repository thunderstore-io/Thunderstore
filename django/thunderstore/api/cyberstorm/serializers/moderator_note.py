from rest_framework import serializers


class ModeratorNoteSerializer(serializers.Serializer):
    """Public representation of a moderator note. Authorship is never exposed."""

    id = serializers.IntegerField()  # noqa: A003
    target_type = serializers.CharField()
    content = serializers.CharField()
    version_number = serializers.CharField(allow_null=True)
    is_active = serializers.BooleanField()
    datetime_created = serializers.DateTimeField()
    datetime_updated = serializers.DateTimeField()


class ModeratorNoteListSerializer(serializers.Serializer):
    """
    All of a resource's notes (active and inactive) for the moderator read
    endpoint. Wrapped in an object so the body is always valid JSON, mirroring
    the ``moderator_notes`` list embedded on the public listing/community detail
    payloads.
    """

    moderator_notes = ModeratorNoteSerializer(many=True)


class ModeratorNoteCreateSerializer(serializers.Serializer):
    content = serializers.CharField()


class ModeratorNoteUpdateSerializer(serializers.Serializer):
    # Partial update: send either field. content edits the text; is_active turns
    # the note on/off (reactivating replaces any other active note on the
    # resource).
    content = serializers.CharField(required=False)
    is_active = serializers.BooleanField(required=False)
