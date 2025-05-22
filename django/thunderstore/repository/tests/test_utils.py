from datetime import datetime

import pytest

from thunderstore.repository.factories import PackageFactory, TeamFactory
from thunderstore.repository.package_reference import PackageReference
from thunderstore.repository.utils import (
    does_contain_package,
    has_duplicate_packages,
    has_expired,
    package_exists_in_any_case,
)


@pytest.mark.parametrize(
    ("collection", "reference", "expected"),
    (
        (
            (
                "user1-package-1.0.0",
                "user2-package-1.0.0",
                "user1-another-1.0.0",
            ),
            "user-package-1.0.0",
            False,
        ),
        (
            (
                "user1-package-1.0.0",
                "user2-package-1.0.0",
                "user1-another-1.0.0",
            ),
            "user1-package-1.0.0",
            True,
        ),
        (
            (
                "user1-package-1.0.0",
                "user2-package-1.0.0",
                "user1-another-1.0.0",
            ),
            "user1-another-5.5.0",
            True,
        ),
        (
            (
                "user1-package",
                "user2-package-1.0.0",
                "user1-another-1.0.0",
            ),
            "user1-package-1.0.0",
            True,
        ),
    ),
)
def test_utils_does_contain_package(collection, reference, expected):
    collection = [PackageReference.parse(x) for x in collection]
    reference = PackageReference.parse(reference)
    assert does_contain_package(collection, reference) == expected


@pytest.mark.parametrize(
    ("collection", "expected"),
    (
        (
            (
                "user1-package-1.0.0",
                "user2-package-1.0.0",
                "user1-another-1.0.0",
            ),
            False,
        ),
        (
            (
                "user1-package-1.0.0",
                "user2-package-1.0.0",
                "user1-package-2.0.0",
            ),
            True,
        ),
        (
            (
                "user1-package",
                "user2-package-1.0.0",
                "user1-package-1.0.0",
            ),
            True,
        ),
        (
            (
                "user1-package",
                "user2-package-1.0.0",
                "user1-another-1.0.0",
            ),
            False,
        ),
    ),
)
def test_utils_has_duplicate_packages(collection, expected):
    collection = [PackageReference.parse(x) for x in collection]
    assert has_duplicate_packages(collection) == expected


@pytest.mark.parametrize(
    ("timestamp", "now", "ttl_seconds", "expected"),
    (
        (
            datetime(2023, 1, 1, 12, 10, 39),
            datetime(2023, 1, 1, 12, 10, 59),
            60,
            False,
        ),
        (
            datetime(2023, 1, 1, 12, 10, 39),
            datetime(2023, 1, 1, 12, 11, 39),
            60,
            False,
        ),
        (
            datetime(2023, 1, 1, 12, 10, 39),
            datetime(2023, 1, 1, 12, 11, 40),
            60,
            True,
        ),
        (
            datetime(2023, 1, 1, 12, 10, 39),
            datetime(2023, 1, 1, 12, 3, 40),
            60,
            False,
        ),
    ),
)
def test_utils_has_expired(
    timestamp: datetime,
    now: datetime,
    ttl_seconds: float,
    expected: bool,
) -> None:
    assert has_expired(timestamp, now, ttl_seconds) is expected


@pytest.mark.django_db
def test_package_exists_in_any_case():
    package = PackageFactory(name="case_package")

    assert package_exists_in_any_case(package.owner.name, "case_package")
    assert package_exists_in_any_case(package.owner.name, "CASE_PACKAGE")
    assert not package_exists_in_any_case(package.owner.name, "casepackage")
