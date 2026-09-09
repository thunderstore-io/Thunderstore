from django.db.models import Count, Q
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from thunderstore.api.cyberstorm.services.package_listing import (
    approve_package_listing,
    reject_package_listing,
    set_package_listing_unreviewed,
)
from thunderstore.api.utils import conditional_swagger_auto_schema
from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.models import PackageListing
from thunderstore.repository.views.package._utils import get_moderatable_communities


def get_moderatable_communities_or_403(user):
    communities = get_moderatable_communities(user)
    if not communities:
        raise PermissionDenied(
            "You don't have moderation permissions in any community."
        )
    return communities


class ReviewListingSerializer(serializers.Serializer):
    id = serializers.IntegerField()  # noqa: A003
    community_identifier = serializers.CharField(source="community.identifier")
    community_name = serializers.CharField(source="community.name")
    namespace = serializers.CharField(source="package.namespace.name")
    name = serializers.CharField(source="package.name")
    review_status = serializers.CharField()
    is_review_requested = serializers.BooleanField()
    last_updated = serializers.DateTimeField(source="package.date_updated")
    icon_url = serializers.SerializerMethodField()
    # Surface the existing moderation context so the reviewer can read/edit it
    # in place without opening the Django admin. Coerce nulls to "" so the
    # frontend always gets plain strings to bind to its editable fields.
    rejection_reason = serializers.SerializerMethodField()
    internal_notes = serializers.SerializerMethodField()

    def get_icon_url(self, obj):
        latest = obj.package.latest
        return latest.icon.url if latest and latest.icon else None

    def get_rejection_reason(self, obj):
        return obj.rejection_reason or ""

    def get_internal_notes(self, obj):
        return obj.notes or ""


class ReviewCommunitySerializer(serializers.Serializer):
    identifier = serializers.CharField()
    name = serializers.CharField()
    count = serializers.IntegerField()


class ReviewListingPaginator(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ReviewBulkUpdateSerializer(serializers.Serializer):
    package_listing_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
        # Cap the batch size so a single request can't force unbounded DB work.
        max_length=100,
    )
    status = serializers.ChoiceField(  # noqa: A003
        choices=[
            PackageListingReviewStatus.unreviewed,
            PackageListingReviewStatus.approved,
            PackageListingReviewStatus.rejected,
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


class ModerationReviewPackagesAPIView(ListAPIView):
    """
    Package listings awaiting review, across the communities the authenticated
    user can moderate.

    This is the package-listing target of the generic moderation "review"
    surface (future entities — e.g. comments — get their own sibling view).

    - GET lists the review-requested listings (optionally filtered by free-text
      query `q`, `review_status` and/or `community`).
    - PATCH applies a review status to several listings at once.

    Unlike the public listing endpoints this deliberately surfaces
    rejected/unreviewed listings, so the response is never publicly cached.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ReviewListingSerializer
    pagination_class = ReviewListingPaginator

    @conditional_swagger_auto_schema(
        operation_id="cyberstorm.moderation.review.packages.list",
        responses={200: ReviewListingSerializer(many=True)},
        tags=["cyberstorm"],
    )
    def get(self, request, *args, **kwargs) -> Response:
        return super().get(request, *args, **kwargs)

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

        review_status = self.request.query_params.get("review_status")
        valid_statuses = {
            PackageListingReviewStatus.unreviewed,
            PackageListingReviewStatus.approved,
            PackageListingReviewStatus.rejected,
        }
        if review_status in valid_statuses:
            qs = qs.filter(review_status=review_status)

        community = self.request.query_params.get("community")
        if community:
            qs = qs.filter(community__identifier=community)

        return qs

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        # Surface the communities that actually have items in this moderator's
        # queue so the frontend can offer a (stable) community filter.
        response.data["communities"] = self._queue_communities(request.user)
        return response

    def _queue_communities(self, user):
        communities = get_moderatable_communities_or_403(user)
        rows = (
            PackageListing.objects.active()
            .filter(is_review_requested=True, community_id__in=communities)
            .values("community__identifier", "community__name")
            .annotate(count=Count("id"))
            .order_by("community__name")
        )
        data = [
            {
                "identifier": row["community__identifier"],
                "name": row["community__name"],
                "count": row["count"],
            }
            for row in rows
        ]
        return ReviewCommunitySerializer(data, many=True).data

    @conditional_swagger_auto_schema(
        operation_id="cyberstorm.moderation.review.packages.bulk_update",
        request_body=ReviewBulkUpdateSerializer,
        responses={200: "Success"},
        tags=["cyberstorm"],
    )
    def patch(self, request, *args, **kwargs) -> Response:
        communities = get_moderatable_communities_or_403(request.user)

        serializer = ReviewBulkUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # The per-listing services touch listing.community and
        # listing.package.namespace; fetch them up front to avoid N+1 queries.
        listings = (
            PackageListing.objects.active()
            .filter(
                pk__in=data["package_listing_ids"],
                community_id__in=communities,
            )
            .select_related(
                "community",
                "package",
                "package__namespace",
            )
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
            set_package_listing_unreviewed(
                agent=user, listing=listing, notes=data.get("internal_notes")
            )

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store, private"
        return response
