from django.db.models import Count, Prefetch, QuerySet

from thunderstore.community.models import PackageListing, Q


def prefetch_package_listing_queryset(
    queryset: QuerySet[PackageListing],
) -> QuerySet[PackageListing]:
    from thunderstore.repository.models import PackageVersion

    return queryset.select_related(
        "community",
        "package",
        "package__owner",
        "package__latest",
    ).annotate(
        _rating_score=Count("package__package_ratings"),
    ).prefetch_related(
        "categories",
        "community__sites",
        Prefetch(
            "package__versions",
            queryset=PackageVersion.objects.select_related(
                "package",
                "package__owner",
            ).prefetch_related(
                "dependencies__package__owner",
            ),
        ),
    )


def order_package_listing_queryset(
    queryset: QuerySet[PackageListing],
) -> QuerySet[PackageListing]:
    return queryset.order_by(
        "-package__is_pinned",
        "package__is_deprecated",
        "-package__date_updated",
    )


def get_package_listing_base_queryset(
    community_identifier: str,
) -> QuerySet[PackageListing]:
    return (
        PackageListing.objects.active()
        .filter_by_community_approval_rule()
        .exclude(~Q(community__identifier=community_identifier))
    )


def get_package_listing_queryset(community_identifier: str) -> QuerySet[PackageListing]:
    return order_package_listing_queryset(
        prefetch_package_listing_queryset(
            get_package_listing_base_queryset(community_identifier),
        ),
    )
