from django.db.models import QuerySet

from thunderstore.community.models import PackageListing, Q


def prefetch_package_listing_queryset(
    queryset: QuerySet[PackageListing],
) -> QuerySet[PackageListing]:
    return queryset.select_related(
        "package",
        "package__owner",
        "package__latest",
    ).prefetch_related(
        "package__versions",
        "package__versions__dependencies",
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
        .public_list()
        .exclude(~Q(community__identifier=community_identifier))
    )


def get_package_listing_queryset(community_identifier: str) -> QuerySet[PackageListing]:
    return order_package_listing_queryset(
        prefetch_package_listing_queryset(
            get_package_listing_base_queryset(community_identifier),
        ),
    )
