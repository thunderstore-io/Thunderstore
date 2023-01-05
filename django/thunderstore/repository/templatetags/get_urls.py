from typing import Dict, Union

from django import template

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
def get_page_url(context: Dict, obj: Union[Package, PackageVersion]) -> str:
    if context.get("use_old_urls", None):
        return obj.get_absolute_url()
    else:
        return obj.get_page_url(context["community_identifier"])


@register.simple_tag(takes_context=True)
def get_owner_url(
    context: Dict, obj: Union[Package, PackageVersion, PackageListing]
) -> str:
    if context.get("use_old_urls", None):
        return obj.owner_url
    else:
        if isinstance(obj, PackageListing):
            return obj.owner_url_with_community_identifier
        else:
            return obj.get_owner_url(context["community_identifier"])
