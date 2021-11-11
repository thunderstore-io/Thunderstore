import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from thunderstore.community.models import PackageListing
from thunderstore.repository.api.v1.serializers import PackageListingSerializer
from thunderstore.repository.cache import get_package_listing_queryset
from thunderstore.repository.factories import (
    PackageFactory,
    PackageVersionFactory,
    TeamFactory,
)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "package_count, version_count",
    [
        (1, 1),
        (1, 5),
        (5, 1),
        (2, 4),
        (5, 5),
    ],
)
def test_package_query_count(
    django_assert_max_num_queries, package_count, version_count, community_site
):
    with CaptureQueriesContext(connection) as context:
        for package_id in range(package_count):
            package = PackageFactory.create(
                owner=TeamFactory.create(name=f"team_{package_id}"),
                name=f"package_{package_id}",
            )
            for version_id in range(version_count):
                PackageVersionFactory.create(
                    package=package,
                    name=f"package_{package_id}",
                    version_number=f"{version_id}.0.0",
                )
            PackageListing.objects.create(
                package=package, community=community_site.community
            )
        creation_queries = len(context)

    packages = get_package_listing_queryset(community_site)
    with django_assert_max_num_queries(package_count + creation_queries + 1):
        serializer = PackageListingSerializer(
            packages, many=True, context={"community_site": community_site}
        )
        _ = serializer.data
