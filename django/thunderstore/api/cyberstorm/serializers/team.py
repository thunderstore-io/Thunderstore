from typing import Optional

from rest_framework import serializers

from thunderstore.api.cyberstorm.serializers.shared import (
    CyberstormPackageCategorySerializer,
    CyberstormPackageListingSectionSerializer,
)
from thunderstore.community.models import PackageCategory, PackageListingSection
from thunderstore.social.utils import get_avatar_url


class CyberstormTeamSerializer(serializers.Serializer):
    """
    This is for team's public profile and readably by anyone. Don't add
    any sensitive information here.

    package_categories and sections will be populated only if a
    `community` query parameter is used with the request.
    """

    identifier = serializers.IntegerField(source="id")
    name = serializers.CharField()
    donation_link = serializers.CharField(required=False)
    package_categories = serializers.SerializerMethodField()
    sections = serializers.SerializerMethodField()

    def get_package_categories(self, obj):
        community_id = self.context["request"].GET.get("community")

        if community_id:
            categories = PackageCategory.objects.filter(
                community__identifier=community_id,
            )
        else:
            categories = PackageCategory.objects.none()

        return CyberstormPackageCategorySerializer(categories, many=True).data

    def get_sections(self, obj):
        community_id = self.context["request"].GET.get("community")

        if community_id:
            sections = (
                PackageListingSection.objects.listed()
                .filter(community__identifier=community_id)
                .order_by("priority")
            )
        else:
            sections = PackageListingSection.objects.none()

        return CyberstormPackageListingSectionSerializer(sections, many=True).data


class CyberstormTeamMemberSerializer(serializers.Serializer):
    identifier = serializers.IntegerField(source="user.id")
    username = serializers.CharField(source="user.username")
    avatar = serializers.SerializerMethodField()
    role = serializers.CharField()

    def get_avatar(self, obj) -> Optional[str]:
        return get_avatar_url(obj.user)


class CyberstormServiceAccountSerializer(serializers.Serializer):
    identifier = serializers.CharField(source="uuid")
    name = serializers.CharField(source="user.first_name")
    last_used = serializers.DateTimeField()
