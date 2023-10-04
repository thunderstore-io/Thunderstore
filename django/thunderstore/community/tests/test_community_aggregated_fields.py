import pytest

from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.factories import CommunityFactory, PackageListingFactory
from thunderstore.community.models import CommunityAggregatedFields


@pytest.mark.django_db
def test_community__without_aggregated_fields_relation__returns_empty_values():
    community = CommunityFactory()

    assert community.aggregated_fields is None
    assert community.aggregated.download_count == 0
    assert community.aggregated.package_count == 0


@pytest.mark.django_db
def test_community__with_aggregated_fields_relation__returns_actual_values():
    caf = CommunityAggregatedFields.objects.create(
        download_count=123,
        package_count=456,
    )
    community = CommunityFactory(aggregated_fields=caf)

    assert community.aggregated_fields is not None
    assert community.aggregated.download_count == 123
    assert community.aggregated.package_count == 456


@pytest.mark.django_db
def test_community_aggregated_fields__create_missing__creates_objects_if_needed():
    assert CommunityAggregatedFields.objects.count() == 0

    # Without Communities, the method does nothing.
    CommunityAggregatedFields.create_missing()

    assert CommunityAggregatedFields.objects.count() == 0

    CommunityFactory(aggregated_fields=CommunityAggregatedFields.objects.create())

    assert CommunityAggregatedFields.objects.count() == 1

    # If all Communities already have fields, the method does nothing.
    CommunityAggregatedFields.create_missing()

    assert CommunityAggregatedFields.objects.count() == 1

    CommunityFactory()

    assert CommunityAggregatedFields.objects.count() == 1

    # Creates fields for Communities that don't have them yet.
    CommunityAggregatedFields.create_missing()

    assert CommunityAggregatedFields.objects.count() == 2


@pytest.mark.django_db
def test_community_aggregated_fields__update_for_community__calculates_packages():
    community1 = CommunityFactory(
        aggregated_fields=CommunityAggregatedFields.objects.create(),
    )
    community2 = CommunityFactory(
        aggregated_fields=CommunityAggregatedFields.objects.create(),
    )

    for _ in range(5):
        PackageListingFactory(community_=community1)

    CommunityAggregatedFields.update_for_community(community1)
    CommunityAggregatedFields.update_for_community(community2)

    assert community1.aggregated.package_count == 5
    assert community2.aggregated.package_count == 0

    for _ in range(10):
        pl = PackageListingFactory(community_=community1)
        PackageListingFactory(community_=community2, package=pl.package)

    CommunityAggregatedFields.update_for_community(community1)
    CommunityAggregatedFields.update_for_community(community2)

    assert community1.aggregated.package_count == 15
    assert community2.aggregated.package_count == 10


@pytest.mark.django_db
def test_community_aggregated_fields__update_for_community__calculates_downloads():
    community1 = CommunityFactory(
        aggregated_fields=CommunityAggregatedFields.objects.create(),
    )
    community2 = CommunityFactory(
        aggregated_fields=CommunityAggregatedFields.objects.create(),
    )
    community3 = CommunityFactory(
        aggregated_fields=CommunityAggregatedFields.objects.create(),
    )

    PackageListingFactory(
        community_=community2,
        package_version_kwargs={"downloads": 0},
    )
    PackageListingFactory(
        community_=community3,
        package_version_kwargs={"downloads": 1},
    )

    CommunityAggregatedFields.update_for_community(community1)
    CommunityAggregatedFields.update_for_community(community2)
    CommunityAggregatedFields.update_for_community(community3)

    assert community1.aggregated.download_count == 0
    assert community2.aggregated.download_count == 0
    assert community3.aggregated.download_count == 1

    listing = PackageListingFactory(
        community_=community2,
        package_version_kwargs={"downloads": 2},
    )
    PackageListingFactory(community_=community3, package=listing.package)

    CommunityAggregatedFields.update_for_community(community1)
    CommunityAggregatedFields.update_for_community(community2)
    CommunityAggregatedFields.update_for_community(community3)

    assert community1.aggregated.download_count == 0
    assert community2.aggregated.download_count == 2
    assert community3.aggregated.download_count == 3


@pytest.mark.django_db
def test_community_aggregated_fields__update_for_community__skips_inactive_packages():
    listing = PackageListingFactory()
    listing.community.aggregated_fields = CommunityAggregatedFields.objects.create()
    listing.community.save()

    CommunityAggregatedFields.update_for_community(listing.community)

    assert listing.community.aggregated.package_count == 1

    listing.package.is_active = False
    listing.package.save()
    CommunityAggregatedFields.update_for_community(listing.community)

    assert listing.community.aggregated.package_count == 0


@pytest.mark.django_db
def test_community_aggregated_fields__update_for_community__skips_unapproved_packages():
    community = CommunityFactory(
        aggregated_fields=CommunityAggregatedFields.objects.create(),
        require_package_listing_approval=True,
    )
    listing1 = PackageListingFactory(
        community_=community,
        review_status=PackageListingReviewStatus.unreviewed,
    )
    listing2 = PackageListingFactory(
        community_=community,
        review_status=PackageListingReviewStatus.rejected,
    )

    CommunityAggregatedFields.update_for_community(community)

    assert community.aggregated.package_count == 0

    listing1.review_status = PackageListingReviewStatus.approved
    listing1.save()
    listing2.review_status = PackageListingReviewStatus.approved
    listing2.save()
    CommunityAggregatedFields.update_for_community(community)

    assert community.aggregated.package_count == 2
