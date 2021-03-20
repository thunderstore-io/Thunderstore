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


@pytest.mark.django_db
def test_package_version_manager_active():
    p1 = PackageVersionFactory(is_active=True)
    p2 = PackageVersionFactory(is_active=False)

    active_versions = PackageVersion.objects.active()
    assert p1 in active_versions
    assert p2 not in active_versions
