from django.db.models import CharField, Count, OuterRef, QuerySet, Subquery, Sum, Value
from rest_framework import serializers
from rest_framework.generics import RetrieveAPIView, get_object_or_404

from thunderstore.api.cyberstorm.serializers import (
    CyberstormPackageCategorySerializer,
    CyberstormTeamMemberSerializer,
)
from thunderstore.api.utils import CyberstormAutoSchemaMixin
from thunderstore.community.models.package_listing import PackageListing
from thunderstore.repository.models.package import get_package_dependants
from thunderstore.repository.models.package_version import PackageVersion


class DependencySerializer(serializers.Serializer):
    """
    Dependencies of a given PackageVersion, listed in a given Community.

    community_identifier and namespace are not present by default and
    need to be annotated to the object.
    """

    community_identifier = serializers.CharField()
    description = serializers.CharField()
    icon_url = serializers.CharField(source="icon.url")
    name = serializers.CharField()
    namespace = serializers.CharField(source="package.namespace.name")
    version_number = serializers.CharField()


class TeamSerializer(serializers.Serializer):
    """
    Minimal information to present the team on package detail view.
    """

    name = serializers.CharField()
    members = CyberstormTeamMemberSerializer(many=True)


class EmptyStringAsNoneField(serializers.Field):
    """
    Serialize empty string to None and deserialize vice versa.
    """

    def to_representation(self, value):
        return None if value == "" else value

    def to_internal_value(self, data):
        return "" if data is None else data


class ResponseSerializer(serializers.Serializer):
    """
    Data shown on package detail view.

    Expects an annotated and customized CustomListing object.
    """

    categories = CyberstormPackageCategorySerializer(many=True)
    community_identifier = serializers.CharField(source="community.identifier")
    community_name = serializers.CharField(source="community.name")
    datetime_created = serializers.DateTimeField(source="package.latest.date_created")
    dependant_count = serializers.IntegerField(min_value=0)
    dependencies = DependencySerializer(many=True)
    description = serializers.CharField(source="package.latest.description")
    download_count = serializers.IntegerField(min_value=0)
    download_url = serializers.CharField(source="package.latest.full_download_url")
    full_version_name = serializers.CharField(source="package.latest")
    has_changelog = serializers.SerializerMethodField()
    icon_url = serializers.CharField(source="package.latest.icon.url")
    install_url = serializers.CharField(source="package.latest.install_url")
    is_deprecated = serializers.BooleanField(source="package.is_deprecated")
    is_nsfw = serializers.BooleanField(source="has_nsfw_content")
    is_pinned = serializers.BooleanField(source="package.is_pinned")
    last_updated = serializers.DateTimeField(source="package.date_updated")
    latest_version_number = serializers.CharField(
        source="package.latest.version_number",
    )
    name = serializers.CharField(source="package.name")
    namespace = serializers.CharField(source="package.namespace.name")
    rating_count = serializers.IntegerField(min_value=0)
    size = serializers.IntegerField(min_value=0, source="package.latest.file_size")
    team = TeamSerializer(source="package.owner")
    website_url = EmptyStringAsNoneField(source="package.latest.website_url")

    def get_has_changelog(self, listing: PackageListing) -> bool:
        changelog = listing.package.latest.changelog
        return False if changelog is None else bool(changelog.strip())


class PackageDetailAPIView(CyberstormAutoSchemaMixin, RetrieveAPIView):
    serializer_class = ResponseSerializer

    def get_object(self):
        return get_custom_package_detail_listing(
            self.kwargs["community_id"],
            self.kwargs["namespace_id"],
            self.kwargs["package_name"],
        )


class CustomListing(PackageListing):
    class Meta:
        abstract = True

    dependant_count: int
    dependencies: QuerySet[PackageVersion]
    download_count: int
    rating_count: int


def get_custom_package_detail_listing(
    community_id: str,
    namespace_id: str,
    package_name: str,
) -> CustomListing:
    listing_ref = PackageListing.objects.filter(pk=OuterRef("pk"))

    qs = (
        PackageListing.objects.active()
        .filter_by_community_approval_rule()
        .select_related(
            "community",
            "package__latest",
            "package__namespace",
            "package__owner",
        )
        .prefetch_related(
            "categories",
            "package__owner__members",
        )
        .annotate(
            download_count=Subquery(
                listing_ref.annotate(
                    downloads=Sum("package__versions__downloads"),
                ).values("downloads"),
            ),
            rating_count=Subquery(
                listing_ref.annotate(
                    ratings=Count("package__package_ratings"),
                ).values("ratings"),
            ),
        )
    )

    listing = get_object_or_404(
        qs,
        community__identifier=community_id,
        package__namespace__name=namespace_id,
        package__name__iexact=package_name,
    )

    listing.dependant_count = get_package_dependants(listing.package.pk).count()
    listing.dependencies = (
        listing.package.latest.dependencies.active()
        .listed_in(community_id)
        .annotate(
            community_identifier=Value(community_id, CharField()),
        )
        .select_related("package", "package__namespace")
        .order_by("package__namespace__name", "package__name")
    )

    return listing
