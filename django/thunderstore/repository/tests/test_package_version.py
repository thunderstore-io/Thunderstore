import pytest

from thunderstore.repository.factories import PackageVersionFactory
from thunderstore.repository.models import PackageVersion


@pytest.mark.django_db
def test_get_total_used_disk_space():
    assert PackageVersion.get_total_used_disk_space() == 0
    p1 = PackageVersionFactory.create()
    assert PackageVersion.get_total_used_disk_space() == p1.file_size
    p2 = PackageVersionFactory.create(file_size=212312412)
    assert PackageVersion.get_total_used_disk_space() == p1.file_size + p2.file_size
