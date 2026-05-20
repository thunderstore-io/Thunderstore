from django import template

from thunderstore.community.models.community import Community
from thunderstore.repository.models.package_version import PackageVersion

register = template.Library()


@register.filter
def available_game_versions(version: PackageVersion, community: Community):
    return version.available_game_versions(community)
