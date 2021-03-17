import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from thunderstore.community.models import Community, PackageListing
from thunderstore.repository.models import Package


@pytest.mark.django_db
def test_package_listing_only_one_per_community(
    active_package: Package, community: Community
) -> None:
    l1 = PackageListing.objects.create(package=active_package, community=community)
    assert l1.pk
    with pytest.raises(IntegrityError) as exc:
        PackageListing.objects.create(package=active_package, community=community)
    assert "one_listing_per_community" in str(exc.value)


@pytest.mark.django_db
def test_package_listing_community_read_only(
    active_package_listing: PackageListing,
) -> None:
    c = Community.objects.create(name="Test Community")
    with pytest.raises(ValidationError) as exc:
        active_package_listing.community = c
        active_package_listing.save()
    assert "PackageListing.community is read only" in str(exc.value)
