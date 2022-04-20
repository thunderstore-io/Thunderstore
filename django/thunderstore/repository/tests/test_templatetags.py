import pytest
from django.template import RequestContext
from requests import Request

from thunderstore.community.models.package_listing import PackageListing
from thunderstore.repository.templatetags.get_urls import (
    get_community_specific_absolute_url,
    get_download_url,
    get_install_url,
    get_owner_url,
)


@pytest.mark.django_db
def test_get_install_url(community_site, active_package_listing) -> None:
    request = Request()
    request.site = community_site.site
    context = {"request": request}
    assert (
        get_install_url(context, active_package_listing.package.latest)
        == f"ror2mm://v1/install/{community_site.site.domain}/{active_package_listing.package.owner.name}/{active_package_listing.package.name}/{active_package_listing.package.latest.version_number}/"
    )


@pytest.mark.django_db
def test_get_download_url(active_package_listing) -> None:
    assert (
        get_download_url({}, active_package_listing.package.latest)
        == f"/package/download/{active_package_listing.package.owner.name}/{active_package_listing.package.name}/{active_package_listing.package.latest.version_number}/"
    )


@pytest.mark.django_db
def test_get_community_specific_absolute_url(active_package_listing) -> None:
    context = {"community_identifier": active_package_listing.community.identifier}

    # Test with Package
    assert (
        get_community_specific_absolute_url(context, active_package_listing.package)
        == f"/c/{active_package_listing.community.identifier}/p/{active_package_listing.package.owner.name}/{active_package_listing.package.name}/"
    )

    # Test with PackageVersion
    assert (
        get_community_specific_absolute_url(
            context, active_package_listing.package.latest
        )
        == f"/c/{active_package_listing.community.identifier}/p/{active_package_listing.package.owner.name}/{active_package_listing.package.name}/v/{active_package_listing.package.latest.version_number}/"
    )


@pytest.mark.django_db
def test_get_owner_url(active_package_listing) -> None:
    context = {"community_identifier": active_package_listing.community.identifier}

    # Test with Package
    assert (
        get_owner_url(context, active_package_listing.package)
        == f"/c/{active_package_listing.community.identifier}/p/{active_package_listing.package.owner.name}/"
    )

    # Test with PackageVersion
    assert (
        get_owner_url(context, active_package_listing.package.latest)
        == f"/c/{active_package_listing.community.identifier}/p/{active_package_listing.package.owner.name}/"
    )
