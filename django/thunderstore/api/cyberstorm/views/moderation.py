from django.db.models import Q
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.api.cyberstorm.services.package_listing import (
    approve_package_listing,
    reject_package_listing,
)
from thunderstore.api.utils import conditional_swagger_auto_schema
from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.models import PackageListing
from thunderstore.repository.views.package._utils import get_moderatable_communities

# Extra "status" option for the bulk action that moves listings into the review
# queue (the is_review_requested flag) rather than setting a review_status.
REVIEW_QUEUE_STATUS = "review-queue"


def get_moderatable_communities_or_403(user):
    communities = get_moderatable_communities(user)
    if not communities:
        raise PermissionDenied(
            "You don't have moderation permissions in any community."
        )
    return communities


class ReviewQueuePackageSerializer(serializers.Serializer):
    id = serializers.IntegerField()  # noqa: A003
    community_identifier = serializers.CharField(source="community.identifier")
    community_name = serializers.CharField(source="community.name")
    namespace = serializers.CharField(source="package.namespace.name")
    name = serializers.CharField(source="package.name")
    review_status = serializers.CharField()
    is_review_requested = serializers.BooleanField()
    last_updated = serializers.DateTimeField(source="package.date_updated")
    icon_url = serializers.SerializerMethodField()

    def get_icon_url(self, obj):
        latest = obj.package.latest
        return latest.icon.url if latest and latest.icon else None


class ReviewQueuePaginator(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ModerationReviewQueuePackagesAPIView(ListAPIView):
    """
    Packages that have requested review, across the communities the
    authenticated user can moderate.

    Unlike the public listing endpoints this deliberately surfaces
    rejected/unreviewed listings, so the response is never publicly cached.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ReviewQueuePackageSerializer
    pagination_class = ReviewQueuePaginator

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return PackageListing.objects.none()

        communities = get_moderatable_communities_or_403(self.request.user)
        qs = (
            PackageListing.objects.active()
            .filter(is_review_requested=True, community_id__in=communities)
            .select_related(
                "community",
                "package",
                "package__namespace",
                "package__latest",
            )
            .order_by("-datetime_created")
        )

        query = self.request.query_params.get("q")
        if query:
            qs = qs.filter(
                Q(package__name__icontains=query)
                | Q(package__namespace__name__icontains=query)
            )

        return qs

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store, private"
        return response


class ReviewQueueBulkActionSerializer(serializers.Serializer):
    package_listing_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
    )
    status = serializers.ChoiceField(  # noqa: A003
        choices=[
            PackageListingReviewStatus.unreviewed,
            PackageListingReviewStatus.approved,
            PackageListingReviewStatus.rejected,
            REVIEW_QUEUE_STATUS,
        ],
    )
    rejection_reason = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )
    internal_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )


class ModerationReviewQueueBulkActionAPIView(APIView):
    """
    Apply a review status (or move into the review queue) to several listings
    at once. Only listings in communities the user can moderate are touched.
    """

    permission_classes = [IsAuthenticated]

    @conditional_swagger_auto_schema(
        operation_id="cyberstorm.moderation.review_queue.bulk_action",
        request_body=ReviewQueueBulkActionSerializer,
        responses={200: "Success"},
        tags=["cyberstorm"],
    )
    def post(self, request, *args, **kwargs) -> Response:
        communities = get_moderatable_communities_or_403(request.user)

        serializer = ReviewQueueBulkActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        listings = PackageListing.objects.active().filter(
            pk__in=data["package_listing_ids"],
            community_id__in=communities,
        )

        updated = 0
        for listing in listings:
            self._apply_status(request.user, listing, data)
            updated += 1

        return Response({"updated": updated}, status=status.HTTP_200_OK)

    def _apply_status(self, user, listing, data) -> None:
        new_status = data["status"]

        if new_status == PackageListingReviewStatus.approved:
            approve_package_listing(
                agent=user,
                notes=data.get("internal_notes"),
                listing=listing,
            )
        elif new_status == PackageListingReviewStatus.rejected:
            reject_package_listing(
                agent=user,
                reason=data.get("rejection_reason") or "",
                notes=data.get("internal_notes"),
                listing=listing,
            )
        elif new_status == PackageListingReviewStatus.unreviewed:
            listing.community.ensure_user_can_moderate_packages(user)
            listing.review_status = PackageListingReviewStatus.unreviewed
            listing.save(update_fields=("review_status",))
        elif new_status == REVIEW_QUEUE_STATUS:
            listing.community.ensure_user_can_moderate_packages(user)
            listing.request_review()
