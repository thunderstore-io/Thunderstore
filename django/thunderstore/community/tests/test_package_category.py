import pytest
from django.db import IntegrityError, transaction

from thunderstore.community.models import Community, PackageCategory


@pytest.mark.django_db
def test_package_category_one_slug_per_community(community: Community) -> None:
    PackageCategory.objects.create(name="Test", slug="test", community=community)
    with transaction.atomic():
        with pytest.raises(IntegrityError) as e:
            PackageCategory.objects.create(
                name="Another test", slug="test", community=community
            )
        assert (
            'duplicate key value violates unique constraint "unique_category_slug_per_community"'
            in str(e.value)
        )
    c2 = Community.objects.create(name="second community")
    assert (
        PackageCategory.objects.create(name="Test", slug="test", community=c2).pk
        is not None
    )
