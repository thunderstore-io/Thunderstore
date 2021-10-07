import pytest
from django.http import Http404

from thunderstore.community.models import Community, PackageListing
from thunderstore.repository.package_reference import PackageReference
from thunderstore.repository.utils import (
    does_contain_package,
    get_listing,
    has_duplicate_packages,
    solve_listing,
)


@pytest.mark.parametrize(
    "collection, reference, expected",
    [
        [
            [
                "user1-package-1.0.0",
                "user2-package-1.0.0",
                "user1-another-1.0.0",
            ],
            "user-package-1.0.0",
            False,
        ],
        [
            [
                "user1-package-1.0.0",
                "user2-package-1.0.0",
                "user1-another-1.0.0",
            ],
            "user1-package-1.0.0",
            True,
        ],
        [
            [
                "user1-package-1.0.0",
                "user2-package-1.0.0",
                "user1-another-1.0.0",
            ],
            "user1-another-5.5.0",
            True,
        ],
        [
            [
                "user1-package",
                "user2-package-1.0.0",
                "user1-another-1.0.0",
            ],
            "user1-package-1.0.0",
            True,
        ],
    ],
)
def test_utils_does_contain_package(collection, reference, expected):
    collection = [PackageReference.parse(x) for x in collection]
    reference = PackageReference.parse(reference)
    assert does_contain_package(collection, reference) == expected


@pytest.mark.parametrize(
    "collection, expected",
    [
        [
            [
                "user1-package-1.0.0",
                "user2-package-1.0.0",
                "user1-another-1.0.0",
            ],
            False,
        ],
        [
            [
                "user1-package-1.0.0",
                "user2-package-1.0.0",
                "user1-package-2.0.0",
            ],
            True,
        ],
        [
            [
                "user1-package",
                "user2-package-1.0.0",
                "user1-package-1.0.0",
            ],
            True,
        ],
        [
            [
                "user1-package",
                "user2-package-1.0.0",
                "user1-another-1.0.0",
            ],
            False,
        ],
    ],
)
def test_utils_has_duplicate_packages(collection, expected):
    collection = [PackageReference.parse(x) for x in collection]
    assert has_duplicate_packages(collection) == expected


@pytest.mark.django_db
def test_get_listing(active_package, active_package_listing, community):
    community_2 = Community.objects.create(name="Test2", identifier="test2")
    community_3 = Community.objects.create(name="Test3", identifier="test3")
    active_listing_2 = PackageListing.objects.create(
        community=community_2,
        package=active_package,
    )
    # Try picking the first listing in defined community
    listing = get_listing(active_package.owner, active_package.name, community)
    assert listing == active_package_listing
    assert listing.community == active_package_listing.community
    assert listing.package.name == active_package_listing.package.name
    assert listing.package.owner.name == active_package_listing.package.owner.name
    # Try picking the second listing of the same package in another community
    listing = get_listing(active_package.owner, active_package.name, community_2)
    assert listing == active_listing_2
    assert listing.community == active_listing_2.community
    assert listing.package.name == active_listing_2.package.name
    assert listing.package.owner.name == active_listing_2.package.owner.name
    # Try to solve if community is not given
    listing = get_listing(active_package.owner, active_package.name, None)
    assert listing == active_package_listing
    assert listing.community == active_package_listing.community
    assert listing.package.name == active_package_listing.package.name
    assert listing.package.owner.name == active_package_listing.package.owner.name
    # Test owner resolving with owner as string
    listing = get_listing(active_package.owner.name, active_package.name, community)
    assert listing == active_package_listing
    assert listing.community == active_package_listing.community
    assert listing.package.name == active_package_listing.package.name
    assert listing.package.owner.name == active_package_listing.package.owner.name
    # Test logic when owner and name is None
    listing = get_listing(None, None, community)
    assert listing == active_package_listing
    assert listing.community == active_package_listing.community
    assert listing.package.name == active_package_listing.package.name
    assert listing.package.owner.name == active_package_listing.package.owner.name
    # Try to find a existing listing in another community
    with pytest.raises(Http404) as exc:
        get_listing(active_package.owner, active_package.name, community_3)
    assert "No matching package found" in str(exc.value)


@pytest.mark.django_db
def test_solve_listing(active_package, active_package_listing):
    # Regular package solve
    assert (
        solve_listing(
            owner=active_package_listing.package.owner,
            name=active_package_listing.package.name,
            community=active_package_listing.community,
        )
        == active_package_listing
    )
    community_2 = Community.objects.create(name="Test2", identifier="test2")
    active_listing_2 = PackageListing.objects.create(
        community=community_2,
        package=active_package,
    )
    # Package solve from another community
    assert (
        solve_listing(
            owner=active_listing_2.package.owner,
            name=active_listing_2.package.name,
            community=active_package_listing.community,
        )
        == active_package_listing
    )
    # Package not found
    with pytest.raises(Http404) as exc:
        solve_listing(owner="Spiderman", name="is not real", community=None)
    assert "No matching package found" in str(exc.value)
