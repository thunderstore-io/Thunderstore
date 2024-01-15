import pytest
from django.core.cache import cache

from thunderstore.modpacks.factories import LegacyProfileFactory
from thunderstore.modpacks.models import LegacyProfile


@pytest.mark.django_db
def test_legacyprofile_manager_get_total_used_disk_space():
    assert LegacyProfile.objects.count() == 0
    assert LegacyProfile.objects.get_total_used_disk_space() == 0

    p1 = LegacyProfileFactory()
    cache.delete(LegacyProfile.objects.size_cache())
    assert LegacyProfile.objects.count() == 1
    assert LegacyProfile.objects.get_total_used_disk_space() == p1.file_size

    p2 = LegacyProfileFactory(file_size=32)
    p3 = LegacyProfileFactory(file_size=32890)
    cache.delete(LegacyProfile.objects.size_cache())
    assert LegacyProfile.objects.count() == 3
    assert LegacyProfile.objects.get_total_used_disk_space() == (
        p1.file_size + p2.file_size + p3.file_size
    )
