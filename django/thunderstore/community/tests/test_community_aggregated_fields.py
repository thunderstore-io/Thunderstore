import pytest

from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.factories import CommunityFactory, PackageListingFactory
from thunderstore.community.models import Community, CommunityAggregatedFields
from thunderstore.community.tasks import update_community_aggregated_fields
from thunderstore.repository.factories import PackageVersionFactory


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


@pytest.mark.django_db
def test_community_aggregated_fields__update_for_community__excludes_cross_community():
    community1 = CommunityFactory(
        aggregated_fields=CommunityAggregatedFields.objects.create(),
    )
    community2 = CommunityFactory(
        aggregated_fields=CommunityAggregatedFields.objects.create(),
    )

    PackageListingFactory(community_=community1)
    PackageListingFactory(community_=community2)

    CommunityAggregatedFields.update_for_community(community1)
    CommunityAggregatedFields.update_for_community(community2)

    assert community1.aggregated.package_count == 1
    assert community2.aggregated.package_count == 1
    assert community1.package_listings.count() == 1
    assert community2.package_listings.count() == 1

    for _ in range(10):
        pl = PackageListingFactory(community_=community1)
        PackageListingFactory(
            community_=community2,
            package=pl.package,
        )
    PackageListingFactory(community_=community1)

    CommunityAggregatedFields.update_for_community(community1)
    CommunityAggregatedFields.update_for_community(community2)

    assert community1.package_listings.count() == 12
    assert community2.package_listings.count() == 11
    assert community1.aggregated.package_count == 2
    assert community2.aggregated.package_count == 1


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
def test_community_aggregated_fields__update_for_community__only_includes_public_list_listings():
    community = CommunityFactory(
        aggregated_fields=CommunityAggregatedFields.objects.create(),
    )
    listing1 = PackageListingFactory(community_=community)
    listing2 = PackageListingFactory(community_=community)

    listing1.visibility.public_list = True
    listing1.visibility.save()
    listing2.visibility.public_list = False
    listing2.visibility.save()

    CommunityAggregatedFields.update_for_community(community)

    assert listing1.visibility.public_list is True
    assert listing2.visibility.public_list is False
    assert community.aggregated.package_count == 1

    listing1.visibility.public_list = True
    listing1.visibility.save()
    listing2.visibility.public_list = True
    listing2.visibility.save()

    CommunityAggregatedFields.update_for_community(community)

    assert listing1.visibility.public_list is True
    assert listing2.visibility.public_list is True
    assert community.aggregated.package_count == 2


@pytest.mark.django_db
def test_community_aggregated_fields__celery_tasks__handles_mixed_situations():
    # Community 1 has existing packages and downloads.
    caf1 = CommunityAggregatedFields.objects.create(package_count=2, download_count=5)
    c1 = CommunityFactory(aggregated_fields=caf1)
    PackageListingFactory(
        community_=c1,
        package_version_kwargs={"downloads": 1},
    )
    c1_l2 = PackageListingFactory(
        community_=c1,
        package_version_kwargs={"downloads": 2, "version_number": "1.0.1"},
    )
    PackageVersionFactory(package=c1_l2.package, downloads=2)

    # Community 1 has changes not reflected in the initial aggregated values.
    PackageListingFactory(
        community_=c1,
        package_version_kwargs={"downloads": 2},
    )

    # Community 2 has existing CommunityAggregatedFields but no packages.
    caf2 = CommunityAggregatedFields.objects.create()
    CommunityFactory(aggregated_fields=caf2)

    # Community 3 has no pre-existing CommunityAggregatedFields.
    c3_l1 = PackageListingFactory(
        package_version_kwargs={"downloads": 3},
    )

    assert Community.objects.count() == 3
    assert CommunityAggregatedFields.objects.count() == 2
    assert caf1.package_count == 2
    assert caf1.download_count == 5
    assert caf2.package_count == 0
    assert caf2.download_count == 0

    update_community_aggregated_fields()
    caf1.refresh_from_db()
    caf2.refresh_from_db()
    caf3 = Community.objects.get(pk=c3_l1.community.pk).aggregated_fields

    assert Community.objects.count() == 3
    assert CommunityAggregatedFields.objects.count() == 3
    assert caf1.package_count == 3
    assert caf1.download_count == 7
    assert caf2.package_count == 0
    assert caf2.download_count == 0
    assert caf3.package_count == 1
    assert caf3.download_count == 3
