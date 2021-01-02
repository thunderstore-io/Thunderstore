import pytest

from thunderstore.repository.package_reference import PackageReference
from thunderstore.repository.utils import does_contain_package, has_duplicate_packages


@pytest.mark.parametrize(
    "collection, reference, expected",
    [
        [
            [
                "user1-package-1.0.0",
                "user2-package-1.0.0",
                "user1-another-1.0.0",
            ],
            "user-package-1.0.0",
            False,
        ],
        [
            [
                "user1-package-1.0.0",
                "user2-package-1.0.0",
                "user1-another-1.0.0",
            ],
            "user1-package-1.0.0",
            True,
        ],
        [
            [
                "user1-package-1.0.0",
                "user2-package-1.0.0",
                "user1-another-1.0.0",
            ],
            "user1-another-5.5.0",
            True,
        ],
        [
            [
                "user1-package",
                "user2-package-1.0.0",
                "user1-another-1.0.0",
            ],
            "user1-package-1.0.0",
            True,
        ],
    ],
)
def test_utils_does_contain_package(collection, reference, expected):
    collection = [PackageReference.parse(x) for x in collection]
    reference = PackageReference.parse(reference)
    assert does_contain_package(collection, reference) == expected


@pytest.mark.parametrize(
    "collection, expected",
    [
        [
            [
                "user1-package-1.0.0",
                "user2-package-1.0.0",
                "user1-another-1.0.0",
            ],
            False,
        ],
        [
            [
                "user1-package-1.0.0",
                "user2-package-1.0.0",
                "user1-package-2.0.0",
            ],
            True,
        ],
        [
            [
                "user1-package",
                "user2-package-1.0.0",
                "user1-package-1.0.0",
            ],
            True,
        ],
        [
            [
                "user1-package",
                "user2-package-1.0.0",
                "user1-another-1.0.0",
            ],
            False,
        ],
    ],
)
def test_utils_has_duplicate_packages(collection, expected):
    collection = [PackageReference.parse(x) for x in collection]
    assert has_duplicate_packages(collection) == expected
