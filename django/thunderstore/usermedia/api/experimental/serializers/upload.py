from rest_framework import serializers

from thunderstore.usermedia.models import UserMedia


class UserMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserMedia
        fields = (
            "uuid",
            "datetime_created",
            "expiry",
            "status",
        )


class UploadPartUrlSerializer(serializers.Serializer):
    part_number = serializers.IntegerField()
    url = serializers.URLField()


class UserMediaUploadUrlsSerializer(serializers.Serializer):
    upload_urls = serializers.ListField(
        child=UploadPartUrlSerializer(),
        allow_empty=False,
    )
    part_size = serializers.IntegerField(required=True)


class UserMediaCreatePartUploadUrlsParams(serializers.Serializer):
    file_size_bytes = serializers.IntegerField(required=True)


class CompletedPartSerializer(serializers.Serializer):
    ETag = serializers.CharField()
    PartNumber = serializers.IntegerField()


class UserMediaFinishUploadParamsSerializer(serializers.Serializer):
    parts = serializers.ListField(
        child=CompletedPartSerializer(),
        allow_empty=False,
    )
