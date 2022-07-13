from typing import List

import pytest

from thunderstore.repository.admin.actions import activate, deactivate
from thunderstore.repository.factories import PackageVersionFactory
from thunderstore.repository.models import Package, PackageVersion


@pytest.mark.django_db
def test_admin_actions_activate() -> None:
    versions: List[PackageVersion] = [
        PackageVersionFactory(is_active=False) for _ in range(5)
    ]
    packages: List[Package] = [x.package for x in versions]
    for p in packages:
        p.is_active = False
        p.save()
    assert all([x.is_active is False for x in versions])
    assert all([x.is_active is False for x in packages])
    activate(None, None, Package.objects.all())
    activate(None, None, PackageVersion.objects.all())
    [x.refresh_from_db() for x in versions]
    [x.refresh_from_db() for x in packages]
    assert all([x.is_active is True for x in versions])
    assert all([x.is_active is True for x in packages])


@pytest.mark.django_db
def test_admin_actions_deactivate() -> None:
    versions: List[PackageVersion] = [PackageVersionFactory() for _ in range(5)]
    packages: List[Package] = [x.package for x in versions]
    assert all([x.is_active is True for x in versions])
    assert all([x.is_active is True for x in packages])
    deactivate(None, None, Package.objects.all())
    deactivate(None, None, PackageVersion.objects.all())
    [x.refresh_from_db() for x in versions]
    [x.refresh_from_db() for x in packages]
    assert all([x.is_active is False for x in versions])
    assert all([x.is_active is False for x in packages])
