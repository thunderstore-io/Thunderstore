import itertools
import random
from datetime import datetime
from typing import Dict

import pytest
from django.http import Http404, HttpRequest
from django.urls import reverse
from rest_framework.test import APIClient

from thunderstore.api.cyberstorm.views import PackageDetailAPIView
from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.factories import CommunitySiteFactory, PackageListingFactory
from thunderstore.community.models import CommunitySite
from thunderstore.community.models.community import Community
from thunderstore.community.models.package_listing import PackageListing
from thunderstore.community.utils import get_preferred_community
from thunderstore.core.factories import UserFactory
from thunderstore.repository.factories import (
    PackageFactory,
    PackageRatingFactory,
    PackageVersionFactory,
)
from thunderstore.repository.models import Package, Team
from thunderstore.repository.models.package_version import PackageVersion


@pytest.mark.django_db
@pytest.mark.parametrize("community_multiplier", (1, 25))
@pytest.mark.parametrize("team_multiplier", (1, 5))
@pytest.mark.parametrize("package_multiplier", (1, 25))
@pytest.mark.parametrize("package_version_multiplier", (1, 10))
def test_api_cyberstorm_package_detail_success(
    api_client: APIClient,
    community_site: CommunitySite,
    community_multiplier: int,
    team_multiplier: int,
    package_multiplier: int,
    package_version_multiplier: int,
):
    def package_version_gen(n, package):
        count = 0
        while count < n:
            yield PackageVersionFactory.build(
                name=package.name,
                package=package,
                is_active=True,
                version_number=f"{count}.0.0",
            )
            count += 1

    def package_gen(n, teams):
        count = 0
        while count < n:
            team = random.choice(teams)
            namespace = team.get_namespace()
            p = PackageFactory.build(
                is_active=True,
                is_deprecated=False,
                owner=team,
                namespace=namespace,
                name=f"{team.name}_package_{count}",
            )
            yield p
            count += 1

    def package_listing_gen(packages, communities):
        count = 0
        combos = list(itertools.product(range(len(packages)), range(len(communities))))
        random.shuffle(combos)
        while count < community_multiplier or count > len(combos):
            pc, cc = combos[count]
            # TODO: Add categories. Categories need to be added in community gen and grabbed here.
            # TODO: Add review status. Review requirement needs to be added in community gen and all status types here.
            # TODO: Add parametrized NSFW.
            # TODO: Add packages without listings.
            p_l = PackageListing(
                community=communities[cc],
                package=packages[pc],
            )
            yield p_l
            count += 1

    # Populate test DB
    coms = Community.objects.bulk_create(
        [
            Community(name=f"Test_{com_count}", identifier=f"test_{com_count}")
            for com_count in range(1, (community_multiplier + 1))
        ]
    )
    teams = Team.objects.bulk_create(
        [
            Team(name=f"Test_Team_{t_count}")
            for t_count in range(1, (team_multiplier + 1))
        ]
    )
    pkgs = Package.objects.bulk_create(package_gen(package_multiplier, teams))
    p_versions = []
    for p in pkgs:
        p_versions += package_version_gen(package_version_multiplier, p)
    PackageVersion.objects.bulk_create(p_versions)
    if len(pkgs) > 2:
        pkgs[2].versions.first().dependencies.set(
            [pkgs[0].versions.first(), pkgs[1].versions.first()]
        )
        pkgs[2].versions.first().save()
    pkg_listings = PackageListing.objects.bulk_create(package_listing_gen(pkgs, coms))

    for pl in pkg_listings:
        # Update latest versions
        pl.package.handle_updated_version(None)
        data = __query_api(
            api_client,
            pl.community.identifier,
            pl.package.namespace.name,
            pl.package.name,
        )

        total = 0
        for x in pl.package.versions.all():
            total += x.downloads

        assert data["name"] == pl.package.name
        assert data["namespace"] == pl.package.namespace.name
        assert data["community"] == pl.community.identifier
        assert data["download_count"] == total
        assert data["likes"] == pl.package.package_ratings.count()
        assert data["author"] == pl.package.owner.name
        assert data["is_pinned"] == pl.package.is_pinned
        assert data["is_nsfw"] == pl.has_nsfw_content
        assert data["is_deprecated"] == pl.package.is_deprecated
        assert data["donation_link"] == pl.package.owner.donation_link
        assert (
            datetime.fromisoformat(data["first_uploaded"].replace("Z", "+00:00"))
            == pl.package.date_created
        )
        for cat in data["categories"]:
            assert pl.categories.filter(name=cat["name"], slug=cat["slug"]).exists()
        assert data["dependant_count"] == len(pl.package.latest.dependencies.all())
        assert data["team"]["name"] == pl.package.owner.name
        for tm in data["team"]["members"]:
            assert pl.package.owner.members.filter(
                user__username=tm["user"], role=tm["role"]
            ).exists()
        for dep in data["dependencies"]:
            preferred = get_preferred_community(
                Package.objects.get(
                    name=dep["name"],
                    namespace__name=dep["namespace"],
                ),
                pl.community,
            )
            if not dep["community"] == None:
                assert preferred.identifier == dep["community"]
            else:
                assert preferred == None
            assert pl.package.latest.dependencies.filter(
                name=dep["name"],
                package__namespace__name=dep["namespace"],
                description=dep["short_description"],
                version_number=dep["version"],
            ).exists()
        assert data["short_description"] == pl.package.latest.description
        assert data["size"] == pl.package.latest.file_size
        assert data["description"] == pl.package.latest.readme
        assert data["github_link"] == pl.package.latest.website_url
        assert (
            datetime.fromisoformat(data["last_updated"].replace("Z", "+00:00"))
            == pl.package.date_updated
        )
        assert data["dependency_string"] == pl.package.latest.full_version_name

        for ver in data["versions"]:
            assert pl.package.versions.filter(
                date_created=datetime.fromisoformat(
                    ver["upload_date"].replace("Z", "+00:00")
                ),
                downloads=ver["download_count"],
                version_number=ver["version"],
                changelog=ver["changelog"],
            ).exists()


@pytest.mark.django_db
def test_api_cyberstorm_package_detail_can_be_viewed_by_user_failure() -> None:
    pl = PackageListingFactory(review_status=PackageListingReviewStatus.rejected)
    view = PackageDetailAPIView()
    user = UserFactory()
    request = HttpRequest()
    setattr(request, "user", user)
    with pytest.raises(Http404) as e_info:
        view.get(
            request, pl.community.identifier, pl.package.namespace.name, pl.package.name
        )
    assert str(e_info.value) == ""


@pytest.mark.django_db
def test_api_cyberstorm_package_detail_package_rating_and_download_counts(
    api_client: APIClient,
) -> None:

    # 1 Community
    site1 = CommunitySiteFactory()
    listing1 = PackageListingFactory(community_=site1.community)
    PackageRatingFactory(package=listing1.package)
    assert listing1.package.package_ratings.count() == 1
    __assert_downloads(listing1, 0)

    data = __query_api(
        api_client,
        site1.community.identifier,
        listing1.package.namespace.name,
        listing1.package.name,
    )
    assert data["likes"] == 1
    assert data["download_count"] == 0

    # 2 Communities
    site2 = CommunitySiteFactory()
    listing2 = PackageListingFactory(
        package_=listing1.package, community_=site2.community
    )
    for x in range(1, 6):
        PackageRatingFactory(package=listing2.package)
        PackageVersionFactory(
            package=listing2.package, downloads=5, version_number=f"{1+x}.0.0"
        )

    assert listing1.package.package_ratings.count() == 6
    __assert_downloads(listing1, 25)

    assert listing2.package.package_ratings.count() == 6
    __assert_downloads(listing2, 25)

    data = __query_api(
        api_client,
        site2.community.identifier,
        listing2.package.namespace.name,
        listing2.package.name,
    )
    assert data["likes"] == 6
    assert data["download_count"] == 25

    # 3 Communities
    site3 = CommunitySiteFactory()
    listing3 = PackageListingFactory(
        package_=listing1.package, community_=site3.community
    )
    for x in range(1, 4):
        PackageRatingFactory(package=listing3.package)
        PackageVersionFactory(
            package=listing3.package, downloads=123, version_number=f"{6+x}.0.0"
        )

    assert listing1.package.package_ratings.count() == 9
    __assert_downloads(listing1, 394)

    assert listing2.package.package_ratings.count() == 9
    __assert_downloads(listing2, 394)

    assert listing3.package.package_ratings.count() == 9
    __assert_downloads(listing3, 394)

    data = __query_api(
        api_client,
        site3.community.identifier,
        listing3.package.namespace.name,
        listing3.package.name,
    )
    assert data["likes"] == 9
    assert data["download_count"] == 394


def __query_api(
    client: APIClient,
    community_id: str,
    package_namespace: str,
    package_name: str,
    response_status_code=200,
) -> Dict:
    url = reverse(
        "api:cyberstorm:cyberstorm.package",
        kwargs={
            "community_id": community_id,
            "package_namespace": package_namespace,
            "package_name": package_name,
        },
    )
    response = client.get(f"{url}")
    assert response.status_code == response_status_code
    return response.json()


def __assert_downloads(listing, count):
    total = 0
    for x in listing.package.versions.all():
        total += x.downloads
    assert total == count
