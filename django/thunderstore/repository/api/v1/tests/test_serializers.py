from typing import Any

import pytest

from thunderstore.community.factories import (
    CommunityFactory,
    CommunitySiteFactory,
    PackageListingFactory,
    SiteFactory,
)
from thunderstore.repository.api.v1.serializers import PackageListingSerializer
from thunderstore.repository.factories import PackageFactory


@pytest.mark.django_db
@pytest.mark.parametrize("use_site", (False, True))
@pytest.mark.parametrize("protocol", ("http://", "https://"))
def test_api_v1_serializers_package_url(
    settings: Any,
    use_site: bool,
    protocol: str,
) -> None:
    community = CommunityFactory(identifier="test-community")
    package = PackageFactory()
    listing = PackageListingFactory(package=package, community=community)
    primary_host = "primary.example.org"
    community_host = "community.example.org"

    if use_site:
        CommunitySiteFactory(
            site=SiteFactory(domain=community_host),
            community=community,
        )

    context = {"community": community}

    settings.PRIMARY_HOST = primary_host
    settings.PROTOCOL = protocol
    expected_prefix = f"/c/{community.identifier}" if not use_site else ""
    expected_host = primary_host if not use_site else community_host
    path_prefix = "/p" if not use_site else "/package"
    expected_path = f"{path_prefix}/{package.namespace.name}/{package.name}/"
    expected_url = f"{protocol}{expected_host}{expected_prefix}{expected_path}"

    serialized = PackageListingSerializer(
        instance=listing,
        context=context,
    ).data
    assert serialized["package_url"] == expected_url
