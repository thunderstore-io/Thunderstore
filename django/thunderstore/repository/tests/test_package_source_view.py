import pytest
from django.urls import reverse

from conftest import TestUserTypes
from thunderstore.community.factories import PackageListingFactory
from thunderstore.community.models import (
    CommunityMemberRole,
    CommunityMembership,
    CommunitySite,
)
from thunderstore.core.enums import OptionalBoolChoice
from thunderstore.frontend.url_reverse import get_community_url_reverse_args
from thunderstore.repository.factories import PackageFactory, PackageVersionFactory
from thunderstore.repository.models import Namespace
from thunderstore.repository.urls import legacy_package_urls, package_urls

all_package_urls = legacy_package_urls + package_urls

HAS_SOURCE_VIEW = "packages.detail.source" in [x.pattern.name for x in all_package_urls]


@pytest.mark.django_db
@pytest.mark.parametrize("user_type", TestUserTypes.options())
@pytest.mark.parametrize("community_role", CommunityMemberRole.options() + [None])
def test_non_public_package_source_roles(
    namespace: Namespace, user_type: str, community_role: str, client, site
):
    # CI pipeline skips this test
    if not HAS_SOURCE_VIEW:
        pytest.skip("Source view is not enabled")

    user = TestUserTypes.get_user_by_type(user_type)
    if user and not user.is_anonymous:
        client.force_login(user)

    team = namespace.team

    package = PackageFactory(owner=team, namespace=namespace)
    package.show_decompilation_results = OptionalBoolChoice.NO
    package.save()
    PackageVersionFactory(package=package)

    listing = PackageListingFactory(package=package)
    listing.community.show_decompilation_results = OptionalBoolChoice.NO
    listing.community.save()

    community_site = CommunitySite.objects.create(
        site=site, community=listing.community
    )

    if community_role is not None and user_type not in TestUserTypes.fake_users():
        CommunityMembership.objects.create(
            user=user,
            role=community_role,
            community=listing.community,
        )

    url = reverse(
        **get_community_url_reverse_args(
            community=listing.community,
            viewname="packages.detail.source",
            kwargs={
                "owner": team,
                "name": package.name,
            },
        )
    )

    response = client.get(
        path=url,
        HTTP_HOST=community_site.site.domain,
    )

    assert response.status_code == 200

    allowed_community_roles = [
        CommunityMemberRole.janitor,
        CommunityMemberRole.moderator,
        CommunityMemberRole.owner,
    ]

    is_visible = False

    if user and user.is_authenticated:
        if user.is_superuser or user.is_staff:
            is_visible = True
        if community_role in allowed_community_roles:
            is_visible = True

    assert response.context["is_visible"] == is_visible
