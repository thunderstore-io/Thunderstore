from rest_framework import serializers

from thunderstore.repository.package_upload import MIN_PACKAGE_SIZE
from thunderstore.usermedia.models import UserMedia


class FilenameField(serializers.CharField):
    def to_internal_value(self, data):
        result = super().to_internal_value(data)
        split = result.replace("\\", "/").split("/")
        return split[-1] if split else ""


class UserMediaInitiateUploadParams(serializers.Serializer):
    filename = FilenameField(allow_null=False, allow_blank=False)
    file_size_bytes = serializers.IntegerField(min_value=MIN_PACKAGE_SIZE)


class UserMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserMedia
        fields = (
            "uuid",
            "filename",
            "size",
            "datetime_created",
            "expiry",
            "status",
        )


class UploadPartUrlSerializer(serializers.Serializer):
    part_number = serializers.IntegerField()
    url = serializers.URLField()
    offset = serializers.IntegerField()
    length = serializers.IntegerField()


class UserMediaInitiateUploadResponseSerializer(serializers.Serializer):
    user_media = UserMediaSerializer()
    upload_urls = serializers.ListField(
        child=UploadPartUrlSerializer(),
        allow_empty=False,
    )


class CompletedPartSerializer(serializers.Serializer):
    ETag = serializers.CharField()
    PartNumber = serializers.IntegerField()


class UserMediaFinishUploadParamsSerializer(serializers.Serializer):
    parts = serializers.ListField(
        child=CompletedPartSerializer(),
        allow_empty=False,
    )
