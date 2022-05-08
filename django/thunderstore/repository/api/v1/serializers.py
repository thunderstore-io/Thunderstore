from django.conf import settings
from rest_framework.fields import Field
from rest_framework.serializers import ModelSerializer, SerializerMethodField

from thunderstore.community.models import PackageListing
from thunderstore.repository.models import PackageVersion


class PackageVersionSerializer(ModelSerializer):
    download_url = SerializerMethodField()
    full_name = SerializerMethodField()
    dependencies = SerializerMethodField()

    def get_download_url(self, instance):
        return instance.full_download_url

    def get_full_name(self, instance):
        return instance.full_version_name

    def get_dependencies(self, instance):
        return [
            dependency.full_version_name for dependency in instance.dependencies.all()
        ]

    class Meta:
        model = PackageVersion
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
            "uuid4",
            "file_size",
        )


class RelatedObjectField(Field):
    def __init__(self, relation_name: str, **kwargs):
        self.relation_name = relation_name
        kwargs["source"] = "*"
        kwargs["read_only"] = True
        super().__init__(**kwargs)

    def bind(self, field_name, parent):
        self.field_name = field_name
        super().bind(field_name, parent)

    def to_representation(self, value):
        return getattr(getattr(value, self.relation_name), self.field_name)


class PackageListingSerializer(ModelSerializer):
    name = RelatedObjectField(relation_name="package")
    full_name = SerializerMethodField()
    owner = SerializerMethodField()
    package_url = SerializerMethodField()
    donation_link = SerializerMethodField()
    date_created = RelatedObjectField(relation_name="package")
    date_updated = RelatedObjectField(relation_name="package")
    uuid4 = RelatedObjectField(relation_name="package")
    rating_score = RelatedObjectField(relation_name="package")
    is_pinned = RelatedObjectField(relation_name="package")
    is_deprecated = RelatedObjectField(relation_name="package")
    categories = SerializerMethodField()
    versions = SerializerMethodField()

    def get_versions(self, instance):
        versions = instance.package.available_versions
        return PackageVersionSerializer(versions, many=True, context=self.context).data

    def get_owner(self, instance):
        return instance.package.owner.name

    def get_full_name(self, instance):
        return instance.package.full_package_name

    def get_package_url(self, instance):
        if (community_site := self.context.get("community_site")) is not None:
            return instance.package.get_full_url(site=community_site.site)
        elif (community := self.context.get("community")) is not None:
            path = instance.package.get_page_url(
                community_identifier=community.identifier
            )
            return f"{settings.PROTOCOL}{settings.PRIMARY_HOST}{path}"
        else:
            return instance.package.get_full_url(site=None)

    def get_donation_link(self, instance):
        return instance.package.owner.donation_link

    def get_categories(self, instance):
        return set(instance.categories.all().values_list("name", flat=True))

    def to_representation(self, instance):
        result = super().to_representation(instance)
        # To ensure backwards compatibility is not broken if this field is
        # removed in the future, omit the key entirely if it's not set, forcing
        # clients to support it not existing.
        if not result["donation_link"]:
            del result["donation_link"]
        return result

    class Meta:
        model = PackageListing
        fields = (
            "name",
            "full_name",
            "owner",
            "package_url",
            "donation_link",
            "date_created",
            "date_updated",
            "uuid4",
            "rating_score",
            "is_pinned",
            "is_deprecated",
            "has_nsfw_content",
            "categories",
            "versions",
        )
        depth = 0
