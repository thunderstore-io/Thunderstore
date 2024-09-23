from typing import Optional

from django.db.models import (
    BooleanField,
    CharField,
    Count,
    ExpressionWrapper,
    OuterRef,
    Q,
    QuerySet,
    Subquery,
    Sum,
    Value,
)
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

    community_identifier is not present by default and needs to be
    annotated to the object.

    Description and icon is not shown to clients if the dependency is
    deactivated, since the fields may contain the very reason for the
    deactivation.
    """

    community_identifier = serializers.CharField()
    description = serializers.SerializerMethodField()
    icon_url = serializers.SerializerMethodField()
    is_active = serializers.BooleanField(source="is_effectively_active")
    name = serializers.CharField()
    namespace = serializers.CharField(source="package.namespace.name")
    version_number = serializers.CharField()
    is_removed = serializers.BooleanField()

    def get_description(self, obj: PackageVersion) -> str:
        return (
            obj.description
            if obj.is_effectively_active
            else "This package has been removed."
        )

    def get_icon_url(self, obj: PackageVersion) -> Optional[str]:
        return obj.icon.url if obj.is_effectively_active else None


class TeamSerializer(serializers.Serializer):
    """
    Minimal information to present the team on package detail view.
    """

    name = serializers.CharField()
    members = CyberstormTeamMemberSerializer(many=True, source="public_members")


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
    dependency_count = serializers.IntegerField(min_value=0)
    description = serializers.CharField(source="package.latest.description")
    download_count = serializers.IntegerField(min_value=0)
    download_url = serializers.CharField(source="package.latest.full_download_url")
    full_version_name = serializers.CharField(source="package.latest.full_version_name")
    has_changelog = serializers.BooleanField()
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


class PackageListingAPIView(CyberstormAutoSchemaMixin, RetrieveAPIView):
    serializer_class = ResponseSerializer

    def get_object(self):
        return get_custom_package_listing(
            community_id=self.kwargs["community_id"],
            namespace_id=self.kwargs["namespace_id"],
            package_name=self.kwargs["package_name"],
        )


class CustomListing(PackageListing):
    class Meta:
        abstract = True

    dependant_count: int
    dependencies: QuerySet[PackageVersion]
    dependency_count: int
    download_count: int
    has_changelog: bool
    rating_count: int


def get_custom_package_listing(
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
            has_changelog=ExpressionWrapper(
                Q(package__latest__changelog__isnull=False),
                output_field=BooleanField(),
            ),
        )
    )

    listing = get_object_or_404(
        qs,
        community__identifier=community_id,
        package__namespace__name=namespace_id,
        package__name=package_name,
    )

    dependencies = (
        listing.package.latest.dependencies.listed_in(community_id)
        .annotate(
            community_identifier=Value(community_id, CharField()),
        )
        .select_related("package", "package__namespace")
        .order_by("package__namespace__name", "package__name")
    )

    # Using .count() and slicing on dependencies does two database
    # queries but prevents loading the whole result set into memory.
    listing.dependencies = dependencies[:4]
    listing.dependency_count = dependencies.count()
    listing.dependant_count = get_package_dependants(listing.package.pk).count()

    return listing
