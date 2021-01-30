from rest_framework import serializers
from rest_framework.fields import SerializerMethodField

from thunderstore.community.models import Community, PackageCategory, PackageListing
from thunderstore.repository.models import Package, PackageVersion, UploaderIdentity
from thunderstore.repository.package_upload import PackageUploadForm


class PackageVersionSerializerExperimental(serializers.ModelSerializer):
    download_url = SerializerMethodField()
    full_name = SerializerMethodField()
    dependencies = SerializerMethodField()

    def get_download_url(self, instance):
        url = instance.download_url
        if "request" in self.context:
            url = self.context["request"].build_absolute_uri(instance.download_url)
        return url

    def get_full_name(self, instance):
        return instance.full_version_name

    def get_dependencies(self, instance):
        return [
            dependency.full_version_name for dependency in instance.dependencies.all()
        ]

    class Meta:
        model = PackageVersion
        ref_name = "PackageVersionExperimental"
        fields = (
            "name",
            "full_name",
            "description",
            "icon",
            "version_number",
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
    package_url = SerializerMethodField()
    latest = PackageVersionSerializerExperimental()
    total_downloads = SerializerMethodField()

    def get_owner(self, instance):
        return instance.owner.name

    def get_full_name(self, instance):
        return instance.full_package_name

    def get_package_url(self, instance):
        return instance.get_full_url(self.context["community_site"].site)

    def get_total_downloads(self, instance):
        return instance.downloads

    class Meta:
        model = Package
        ref_name = "PackageExperimental"
        fields = (
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
        )
        depth = 0


class PackageListingSerializerExperimental(serializers.ModelSerializer):
    package = PackageSerializerExperimental()
    categories = SerializerMethodField()

    def get_categories(self, instance):
        return set(instance.categories.all().values_list("name", flat=True))

    class Meta:
        model = PackageListing
        ref_name = "PackageListingExperimental"
        fields = (
            "package",
            "has_nsfw_content",
            "categories",
        )


class PackageUploadAuthorNameField(serializers.SlugRelatedField):
    def __init__(self, *args, **kwargs):
        kwargs["slug_field"] = "name"
        super().__init__(*args, **kwargs)

    def get_queryset(self):
        return UploaderIdentity.objects.filter(
            members__user=self.context["request"].user,
        )


class PackageUploadCategoriesField(serializers.RelatedField):
    def get_queryset(self):
        return PackageCategory.objects.filter(
            community=self.context["request"].community,
        )

    def to_representation(self, value):
        return [c.pk for c in value]

    def to_internal_value(self, data):
        if not isinstance(data, list):
            raise serializers.ValidationError("Not a list")

        out = []
        for category_pk in data:
            category = PackageCategory.objects.filter(pk=category_pk).first()
            if not category:
                raise serializers.ValidationError(f"{category_pk} category not found")
            out.append(category)
        return out


class PackageUploadSerializer(serializers.Serializer):
    author_name = PackageUploadAuthorNameField()
    categories = PackageUploadCategoriesField()
    has_nsfw_content = serializers.BooleanField()
    pk = serializers.IntegerField(read_only=True)
    file = serializers.FileField(write_only=True)

    def _create_form(self, data) -> PackageUploadForm:
        request = self.context["request"]
        return PackageUploadForm(
            request.user,
            data.get("author_name"),
            request.community,
            data={
                "categories": data.get("categories"),
                "has_nsfw_content": data.get("has_nsfw_content"),
            },
            files={"file": data.get("file")},
        )

    def validate(self, data):
        form = self._create_form(data)
        if not form.is_valid():
            raise serializers.ValidationError("Invalid")
        return data

    def create(self, validated_data) -> PackageVersion:
        form = self._create_form(validated_data)
        form.is_valid()
        return form.save()


class UploaderIdentitySerializer(serializers.ModelSerializer):
    class Meta:
        model = UploaderIdentity
        fields = (
            "name",
            "pk",
        )

    def create(self, *args, **kwargs):
        raise Exception()

    def update(self, *args, **kwargs):
        raise Exception()


class PackageSerializer(serializers.ModelSerializer):
    owner = UploaderIdentitySerializer()

    class Meta:
        model = Package
        fields = (
            "owner",
            "name",
            "is_active",
            "is_deprecated",
            "date_created",
            "date_updated",
            "is_pinned",
        )

    def create(self, *args, **kwargs):
        raise Exception()

    def update(self, *args, **kwargs):
        raise Exception()


class PackageVersionSerializer(serializers.ModelSerializer):
    package = PackageSerializer()

    class Meta:
        model = PackageVersion
        fields = (
            "package",
            "is_active",
            "date_created",
            "downloads",
            "name",
            "version_number",
            "website_url",
            "description",
            "dependencies",
            "readme",
            "file_size",
            "pk",
        )

    def create(self, *args, **kwargs):
        raise Exception()

    def update(self, *args, **kwargs):
        raise Exception()
