from rest_framework import serializers

from thunderstore.repository.validation.markdown import MAX_MARKDOWN_SIZE
from thunderstore.wiki.models import WikiPage


class WikiPageBaseSerializer(serializers.Serializer):
    id = serializers.CharField(source="pk")
    title = serializers.CharField(
        max_length=WikiPage._meta.get_field("title").max_length,
    )
    slug = serializers.CharField(source="full_slug")
    datetime_created = serializers.DateTimeField()
    datetime_updated = serializers.DateTimeField()


class WikiPageSerializer(WikiPageBaseSerializer):
    markdown_content = serializers.CharField()


class WikiPageUpsertSerializer(serializers.Serializer):
    id = serializers.CharField(required=False)
    title = serializers.CharField(
        required=True,
        max_length=WikiPage._meta.get_field("title").max_length,
    )
    markdown_content = serializers.CharField(
        required=True,
        max_length=MAX_MARKDOWN_SIZE,
    )


class WikiPageDeleteSerializer(serializers.Serializer):
    id = serializers.CharField(required=True)


class WikiPageIndexSerializer(WikiPageBaseSerializer):
    pass


class WikiSerializer(serializers.Serializer):
    id = serializers.CharField(source="pk")
    title = serializers.CharField()
    slug = serializers.CharField(source="full_slug")
    pages = WikiPageIndexSerializer(many=True)
