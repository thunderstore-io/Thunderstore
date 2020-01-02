import pytest

from repository.api.v1.serializers import PackageSerializer
from repository.cache import get_mod_list_queryset
from repository.factories import PackageVersionFactory, PackageFactory, UploaderIdentityFactory


@pytest.mark.django_db
@pytest.mark.parametrize(
    "package_count, version_count",
    [
        (1, 1),
        (1, 5),
        (5, 1),
        (2, 4),
        (5, 5),
    ]
)
def test_package_query_count(django_assert_max_num_queries, package_count, version_count):
    for package_id in range(package_count):
        package = PackageFactory.create(
            owner=UploaderIdentityFactory.create(
                name=f"uploader_{package_id}"
            ),
            name=f"package_{package_id}",
        )
        for version_id in range(version_count):
            PackageVersionFactory.create(
                package=package,
                name=f"package_{package_id}",
                version_number=f"{version_id}.0.0",
            )

    packages = get_mod_list_queryset()
    with django_assert_max_num_queries(package_count * 5 + 3):
        serializer = PackageSerializer(packages, many=True)
        _ = serializer.data
