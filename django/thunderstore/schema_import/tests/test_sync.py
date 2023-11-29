import pytest

from thunderstore.community.models import (
    Community,
    PackageCategory,
    PackageListingSection,
)
from thunderstore.schema_import.sync import get_slogan_from_display_name
from thunderstore.schema_import.tasks import sync_ecosystem_schema


@pytest.mark.parametrize(
    ("name", "expected"),
    (
        ("Risk of Rain 2", "The Risk of Rain 2 Mod Database"),
        ("The Ouroboros King", "The Ouroboros King Mod Database"),
    ),
)
def test_schema_sync_slogan_name(name: str, expected: str):
    assert get_slogan_from_display_name(name) == expected


@pytest.mark.django_db
def test_schema_sync():
    assert Community.objects.count() == 0
    assert PackageCategory.objects.count() == 0
    assert PackageListingSection.objects.count() == 0

    sync_ecosystem_schema.delay()

    com_count = Community.objects.count()
    cat_count = PackageCategory.objects.count()
    sec_count = PackageListingSection.objects.count()
    assert com_count > 0
    assert cat_count > 0
    assert sec_count > 0

    # Ensure idempotency
    sync_ecosystem_schema.delay()

    assert com_count == Community.objects.count()
    assert cat_count == PackageCategory.objects.count()
    assert sec_count == PackageListingSection.objects.count()
