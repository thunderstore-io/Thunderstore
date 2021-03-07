import pytest
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
