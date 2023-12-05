from rest_framework import serializers

from thunderstore.api.cyberstorm.serializers.community import (
    CyberstormPackageCategorySerializer,
)
from thunderstore.community.models import Community
from thunderstore.repository.models import Namespace, Package, PackageVersion


class CyberstormPackagePreviewSerializer(serializers.Serializer):
    """
    Data shown on "PackageCard" component on frontend.
    """

    categories = CyberstormPackageCategorySerializer(many=True)
    community_identifier = serializers.CharField(
        max_length=Community._meta.get_field("identifier").max_length,
    )
    description = serializers.CharField(
        max_length=PackageVersion._meta.get_field("description").max_length,
    )
    download_count = serializers.IntegerField(min_value=0)
    icon_url = serializers.CharField()
    is_deprecated = serializers.BooleanField()
    is_nsfw = serializers.BooleanField()
    is_pinned = serializers.BooleanField()
    last_updated = serializers.DateTimeField()
    name = serializers.CharField(max_length=Package._meta.get_field("name").max_length)
    namespace = serializers.CharField(
        max_length=Namespace._meta.get_field("name").max_length,
    )
    rating_count = serializers.IntegerField(min_value=0)
    size = serializers.IntegerField(min_value=0)
