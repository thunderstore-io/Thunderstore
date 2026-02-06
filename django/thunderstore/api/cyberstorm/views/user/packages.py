from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated

from thunderstore.api.pagination import PackageListPaginator
from thunderstore.api.utils import CyberstormAutoSchemaMixin
from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.models import PackageListing
from thunderstore.repository.models import Team


class PackageListingReviewStatusSerializer(serializers.Serializer):
    review_status = serializers.CharField()
    rejection_reason = serializers.CharField()

    community_name = serializers.CharField(source="community.name")
    community_identifier = serializers.CharField(source="community.identifier")

    package_icon_url = serializers.CharField(source="package.icon.url")
    package_name = serializers.CharField(source="package.name")
    package_namespace = serializers.CharField(source="package.namespace.name")
    package_owner = serializers.CharField(source="package.owner.name")

    package_date_created = serializers.DateTimeField(source="package.date_created")

    @classmethod
    def get_queryset(cls):
        return PackageListing.objects.select_related(*cls.get_select_related())

    @classmethod
    def get_select_related(cls):
        return ["community", "package", "package__namespace", "package__owner"]


class UserRejectedPackageListingsListAPIView(
    CyberstormAutoSchemaMixin, generics.ListAPIView
):
    pagination_class = PackageListPaginator
    serializer_class = PackageListingReviewStatusSerializer

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        teams = list(
            Team.objects.filter(members__user=self.request.user).values_list(
                "pk", flat=True
            )
        )
        return PackageListingReviewStatusSerializer.get_queryset().filter(
            review_status=PackageListingReviewStatus.rejected,
            package__owner__in=teams,
        )
