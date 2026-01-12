from typing import Optional

import pytest
from django.http import Http404
from rest_framework.test import APIClient

from thunderstore.api.cyberstorm.views.markdown import get_package_version
from thunderstore.repository.factories import PackageVersionFactory
from thunderstore.repository.models import Package


@pytest.mark.django_db
@pytest.mark.parametrize("requested_version", (None, "1.0.0", "1.0.1", "1.2.3"))
def test_get_package_version__returns_requested_version_or_latest_by_default(
    package: Package,
    requested_version: Optional[str],
) -> None:
    PackageVersionFactory(package=package, version_number="1.0.0")
    PackageVersionFactory(package=package, version_number="1.2.3")
    PackageVersionFactory(package=package, version_number="1.0.1")

    actual = get_package_version(
        package.namespace.name,
        package.name,
        requested_version,
    )

    if requested_version:
        assert actual.version_number == requested_version
    else:
        assert actual.version_number == "1.2.3"  # latest


@pytest.mark.django_db
def test_get_package_version__raises_for_inactive_package(
    package: Package,
) -> None:
    PackageVersionFactory(package=package)
    package.is_active = False
    package.save()

    with pytest.raises(Http404):
        get_package_version(package.namespace.name, package.name, None)


@pytest.mark.django_db
@pytest.mark.parametrize("requested_version", (None, "1.0.0"))
def test_get_package_version__raises_for_inactive_package_version(
    package: Package,
    requested_version: Optional[str],
) -> None:
    PackageVersionFactory(package=package, is_active=False)

    with pytest.raises(Http404):
        get_package_version(
            package.namespace.name,
            package.name,
            requested_version,
        )
