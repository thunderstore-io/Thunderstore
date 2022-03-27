from thunderstore.community.models import (
    Community,
    PackageListing,
    PackageListingReviewStatus,
    Q,
)


def get_package_listing_queryset(community: Community):
    return (
        PackageListing.objects.active()
        .exclude(~Q(community=community))
        .exclude(review_status=PackageListingReviewStatus.rejected)
        .exclude(
            Q(community__require_package_listing_approval=True)
            & ~Q(review_status=PackageListingReviewStatus.approved)
        )
        .select_related(
            "package",
            "package__owner",
            "package__latest",
        )
        .prefetch_related(
            "package__versions",
            "package__versions__dependencies",
        )
        .order_by(
            "-package__is_pinned", "package__is_deprecated", "-package__date_updated"
        )
    )
