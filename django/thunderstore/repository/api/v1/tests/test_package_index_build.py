from io import BytesIO

import pytest
from rest_framework.parsers import JSONParser

from thunderstore.community.factories import PackageListingFactory
from thunderstore.community.models import CommunitySite
from thunderstore.repository.api.v1.viewsets import (
    PACKAGE_SERIALIZER,
    SERIALIZER_BATCH_SIZE,
    serialize_package_list_for_community,
)


@pytest.mark.django_db
def test_serialize_package_list_for_community(community_site: CommunitySite):
    for _ in range(int(SERIALIZER_BATCH_SIZE * 2.5)):
        PackageListingFactory(community=community_site.community)
    result = serialize_package_list_for_community(community_site.community)
    buffer = BytesIO(result)
    buffer.seek(0)
    serializer = PACKAGE_SERIALIZER(data=JSONParser().parse(buffer), many=True)
    assert serializer.is_valid(raise_exception=True) is True
