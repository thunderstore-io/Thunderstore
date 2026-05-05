from django.db.models import Q
from rest_framework import serializers
from rest_framework.fields import SerializerMethodField, empty

from thunderstore.community.consts import AI_GENERATED_CATEGORY_SLUG
from thunderstore.community.models import Community, PackageCategory, PackageListing
from thunderstore.core.utils import make_full_url
from thunderstore.frontend.api.experimental.serializers.views import (
    CommunitySerializer,
    PackageCategorySerializer,
)
from thunderstore.repository.models import Package, PackageVersion, Team
from thunderstore.repository.package_upload import PackageUploadForm
from thunderstore.repository.serializer_fields import ModelChoiceField


class PackageListingSerializerExperimental(serializers.ModelSerializer):
    categories = SerializerMethodField()
    community = SerializerMethodField()

    def get_categories(self, instance):
        return [x.name for x in instance.categories.all()]

    def get_community(self, instance):
        return instance.community.identifier

    class Meta:
        model = PackageListing
        ref_name = "PackageListingExperimental"
        fields = (
            "has_nsfw_content",
            "categories",
            "community",
            "review_status",
        )


class PackageVersionSerializerExperimental(serializers.ModelSerializer):
    download_url = SerializerMethodField()
    namespace = SerializerMethodField()
    full_name = SerializerMethodField()
    dependencies = SerializerMethodField()

    def get_download_url(self, instance):
        return instance.full_download_url

    def get_full_name(self, instance):
        return instance.full_version_name

    def get_namespace(self, instance):
        return instance.package.owner.name

    def get_dependencies(self, instance):
        return [
            dependency.full_version_name for dependency in instance.dependencies.all()
        ]

    class Meta:
        model = PackageVersion
        ref_name = "PackageVersionExperimental"
        fields = (
            "namespace",
            "name",
            "version_number",
            "full_name",
            "description",
            "icon",
            "dependencies",
            "download_url",
            "downloads",
            "date_created",
            "website_url",
            "is_active",
        )


class PackageSerializerExperimental(serializers.ModelSerializer):
    owner = SerializerMethodField()
    full_name = SerializerMethodField()
    namespace = SerializerMethodField()
    package_url = SerializerMethodField()
    latest = PackageVersionSerializerExperimental()
    total_downloads = SerializerMethodField()
    rating_score = SerializerMethodField()
    community_listings = PackageListingSerializerExperimental(many=True)

    def get_owner(self, instance):
        return instance.owner.name

    def get_full_name(self, instance):
        return instance.full_package_name

    def get_namespace(self, instance):
        return instance.owner.name

    def get_package_url(self, instance):
        return make_full_url(self.context["request"], instance.get_absolute_url())

    def get_total_downloads(self, instance):
        return -1

    def get_rating_score(self, instance):
        return -1

    class Meta:
        model = Package
        ref_name = "PackageExperimental"
        fields = (
            "namespace",
            "name",
            "full_name",
            "owner",
            "package_url",
            "date_created",
            "date_updated",
            "rating_score",
            "is_pinned",
            "is_deprecated",
            "total_downloads",
            "latest",
            "community_listings",
        )
        depth = 0


class PackageUploadAuthorNameField(serializers.SlugRelatedField):
    """Package upload's author name metadata field."""

    def __init__(self, *args, **kwargs):
        kwargs["slug_field"] = "name"
        super().__init__(*args, **kwargs)

    def get_queryset(self):
        return Team.objects.exclude(
            ~Q(members__user=self.context["request"].user) | Q(is_active=False)
        )


class JSONSerializerField(serializers.JSONField):
    """Parses a JSON string and passes the data to a Serializer."""

    def __init__(self, serializer, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.serializer = serializer

    def bind(self, field_name, parent):
        super().bind(field_name, parent)
        self.serializer.bind(field_name, parent)

    def run_validation(self, data=empty):
        return self.serializer.run_validation(super().run_validation(data))


class CommunityFilteredModelChoiceField(ModelChoiceField):
    def get_queryset(self):
        if "community" in self.context:
            return self.queryset.exclude(
                ~Q(community=self.context["community"]),
            )
        return self.queryset.exclude(
            ~Q(community=self.context["request"].community),
        )


class PackageUploadMetadataSerializer(serializers.Serializer):
    """Non-file fields used for package upload."""

    author_name = PackageUploadAuthorNameField()
    categories = serializers.ListField(
        child=CommunityFilteredModelChoiceField(
            queryset=PackageCategory.objects.all(),
            to_field="slug",
        ),
        allow_empty=True,
        required=False,
    )
    communities = serializers.ListField(
        child=ModelChoiceField(
            queryset=Community.objects.all(),
            to_field="identifier",
        ),
        allow_empty=False,
    )
    has_nsfw_content = serializers.BooleanField()


class PackageUploadSerializerExperiemental(serializers.Serializer):
    file = serializers.FileField(write_only=True)
    metadata = JSONSerializerField(serializer=PackageUploadMetadataSerializer())

    def _create_form(self, data) -> PackageUploadForm:
        request = self.context["request"]
        metadata = data.get("metadata", {})
        return PackageUploadForm(
            user=request.user,
            community=request.community,
            data={
                "categories": metadata.get("categories", []),
                "has_nsfw_content": metadata.get("has_nsfw_content"),
                "team": metadata.get("author_name"),
                "communities": metadata.get("communities"),
            },
            files={"file": data.get("file")},
        )

    def validate(self, data):
        form = self._create_form(data)
        if not form.is_valid():
            raise serializers.ValidationError(form.errors)
        return data

    def create(self, validated_data) -> PackageVersion:
        form = self._create_form(validated_data)
        form.is_valid()
        return form.save()


class PackageSubmissionMetadataSerializer(PackageUploadMetadataSerializer):
    upload_uuid = serializers.UUIDField()
    community_categories = serializers.DictField(
        child=serializers.ListField(
            child=serializers.CharField(allow_blank=False, required=True),
            allow_empty=True,
        ),
        required=False,
    )
    is_ai_generated = serializers.BooleanField(required=False, allow_null=True)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        communities = attrs.get("communities") or []
        is_ai_generated = attrs.get("is_ai_generated")
        attestation_required = any(c.require_ai_attestation for c in communities)

        if attestation_required and is_ai_generated is None:
            raise serializers.ValidationError(
                {
                    "is_ai_generated": [
                        "One or more selected communities requires "
                        "authors to disclose whether AI was used",
                    ],
                },
            )

        if is_ai_generated is not None:
            community_categories = dict(attrs.get("community_categories") or {})
            for community in communities:
                if not community.require_ai_attestation:
                    continue
                slugs = list(community_categories.get(community.identifier) or [])
                has_slug = AI_GENERATED_CATEGORY_SLUG in slugs
                if is_ai_generated and not has_slug:
                    slugs.append(AI_GENERATED_CATEGORY_SLUG)
                elif not is_ai_generated and has_slug:
                    slugs = [s for s in slugs if s != AI_GENERATED_CATEGORY_SLUG]
                community_categories[community.identifier] = slugs
            attrs["community_categories"] = community_categories

        return attrs


class AvailableCommunitySerializer(serializers.Serializer):
    community = CommunitySerializer()
    categories = PackageCategorySerializer(many=True)
    url = serializers.CharField()


class PackageSubmissionResult(serializers.Serializer):
    package_version = PackageVersionSerializerExperimental()
    available_communities = AvailableCommunitySerializer(many=True)
