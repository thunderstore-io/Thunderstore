from rest_framework import serializers


class WikiPageBaseSerializer(serializers.Serializer):
    id = serializers.CharField(source="pk")
    title = serializers.CharField()
    slug = serializers.SerializerMethodField()
    datetime_created = serializers.DateTimeField()
    datetime_updated = serializers.DateTimeField()

    def get_slug(self, instance) -> str:
        return f"{instance.pk}-{instance.slug}"


class WikiPageSerializer(WikiPageBaseSerializer):
    markdown_content = serializers.CharField()


class WikiPageUpsertSerializer(serializers.Serializer):
    id = serializers.CharField(required=False)
    title = serializers.CharField(required=True)
    markdown_content = serializers.CharField(required=True)


class WikiPageIndexSerializer(WikiPageBaseSerializer):
    pass


class WikiSerializer(serializers.Serializer):
    id = serializers.CharField(source="pk")
    title = serializers.CharField()
    slug = serializers.SerializerMethodField()
    pages = WikiPageIndexSerializer(many=True)

    def get_slug(self, instance) -> str:
        return f"{instance.pk}-{instance.slug}"
