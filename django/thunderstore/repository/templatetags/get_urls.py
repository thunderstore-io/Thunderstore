from typing import Dict, Union

from django import template

from thunderstore.community.models.community_site import CommunitySite
from thunderstore.community.models.package_listing import PackageListing
from thunderstore.repository.models.package import Package
from thunderstore.repository.models.package_version import PackageVersion

register = template.Library()


@register.simple_tag(takes_context=True)
def get_install_url(context: Dict, obj: PackageVersion) -> str:
    return obj.get_install_url(context["request"])


@register.simple_tag(takes_context=True)
def get_download_url(context: Dict, obj: PackageVersion) -> str:
    return obj.download_url


@register.simple_tag(takes_context=True)
def get_community_specific_absolute_url(
    context: Dict, obj: Union[Package, PackageVersion]
) -> str:
    return obj.get_community_specific_absolute_url(context["community_identifier"])


@register.simple_tag(takes_context=True)
def get_owner_url(context: Dict, obj: Union[Package, PackageVersion]) -> str:
    return obj.get_owner_url(context["community_identifier"])
