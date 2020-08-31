import pytest

from ..factories import PackageFactory
from ..factories import PackageVersionFactory


@pytest.fixture(scope="function")
def active_package():
    package = PackageFactory.create(
        is_active=True,
        is_deprecated=False,
    )
    PackageVersionFactory.create(
        name=package.name,
        package=package,
        is_active=True,
    )
    return package


@pytest.fixture(scope="function")
def active_version(active_package):
    return active_package.versions.first()
