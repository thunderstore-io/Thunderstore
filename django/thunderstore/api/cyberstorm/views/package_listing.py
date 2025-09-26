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
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import RetrieveAPIView, get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.api.cyberstorm.serializers import (
    CyberstormPackageCategorySerializer,
    CyberstormPackageTeamSerializer,
    EmptyStringAsNoneField,
    PackageListingStatusResponseSerializer,
)
from thunderstore.api.cyberstorm.views.package_listing_actions import (
    get_package_listing,
)
from thunderstore.api.utils import CyberstormAutoSchemaMixin
from thunderstore.community.models.package_listing import PackageListing
from thunderstore.repository.models.package import get_package_dependants
from thunderstore.repository.models.package_version import PackageVersion
from thunderstore.repository.views.package.detail import PermissionsChecker


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
    is_unavailable = serializers.SerializerMethodField()

    def get_description(self, obj: PackageVersion) -> str:
        return (
            obj.description
            if obj.is_effectively_active
            else "This package has been removed."
        )

    def get_icon_url(self, obj: PackageVersion) -> Optional[str]:
        return obj.icon.url if obj.is_effectively_active else None

    def get_is_unavailable(self, obj: PackageVersion) -> bool:
        # Annotated result of PackageVersion.is_unavailable
        # See get_custom_package_listing()
        return obj.version_is_unavailable


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
    version_count = serializers.IntegerField()
    name = serializers.CharField(source="package.name")
    namespace = serializers.CharField(source="package.namespace.name")
    rating_count = serializers.IntegerField(min_value=0)
    size = serializers.IntegerField(min_value=0, source="package.latest.file_size")
    team = CyberstormPackageTeamSerializer(source="package.owner")
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
            version_count=Count(
                "package__versions", filter=Q(package__versions__is_active=True)
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
        .annotate(community_identifier=Value(community_id, CharField()))
        .select_related("package", "package__namespace")
        .order_by("package__namespace__name", "package__name")
    )

    # Using .count() and slicing on dependencies does two database
    # queries but prevents loading the whole result set into memory.
    listing.dependencies = dependencies[:4]

    for dependency in listing.dependencies:
        dependency.version_is_unavailable = dependency.is_unavailable(
            community=listing.community,
        )

    listing.dependency_count = dependencies.count()
    listing.dependant_count = get_package_dependants(listing.package.pk).count()

    return listing


class PackageListingStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PackageListingStatusResponseSerializer

    @swagger_auto_schema(
        operation_id="cyberstorm.package_listing.status",
        responses={200: serializer_class},
        tags=["cyberstorm"],
    )
    def get(
        self, request, namespace_id: str, package_name: str, community_id: str
    ) -> Response:
        package_listing = get_package_listing(
            namespace_id=namespace_id,
            package_name=package_name,
            community_id=community_id,
        )
        checker = PermissionsChecker(package_listing, request.user)

        if not (checker.can_manage or checker.can_moderate):
            error_msg = "You do not have permission to view review information."
            raise PermissionDenied(error_msg)

        response_data = {
            "review_status": None,
            "rejection_reason": None,
            "internal_notes": None,
            "listing_admin_url": None,
        }

        if checker.can_manage:
            response_data["review_status"] = package_listing.review_status
            response_data["rejection_reason"] = package_listing.rejection_reason

        if checker.can_view_listing_admin_page:
            response_data["listing_admin_url"] = package_listing.get_admin_url()

        if checker.can_moderate:
            response_data["internal_notes"] = package_listing.notes

        serializer = self.serializer_class(response_data)
        return Response(serializer.data, status=status.HTTP_200_OK)
