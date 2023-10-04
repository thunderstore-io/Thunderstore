from typing import Optional

from django.conf import settings
from django.db.models import Count
from django.templatetags.static import static

from thunderstore.community.models.community import Community


def get_community_context(community: Optional[Community]):
    if community:
        result = {
            "community": community,
            "community_identifier": community.identifier,
            "community_nav_links": community.nav_links.filter(is_active=True),
            "site_name": settings.SITE_NAME,
            "site_slogan": community.slogan or "",
            "site_description": community.description or "",
            "site_discord_url": community.discord_url or "",
            "site_wiki_url": community.wiki_url or "",
        }
        if community.icon:
            url = community.icon.url
            if not (url.startswith("http://") or url.startswith("https://")):
                url = f"{settings.PROTOCOL}{settings.PRIMARY_HOST}{url}"
            result.update(
                {
                    "site_icon": url,
                    "site_icon_width": community.icon_width,
                    "site_icon_height": community.icon_height,
                }
            )
        else:
            result.update(
                {
                    "site_icon": f"{settings.PROTOCOL}{settings.PRIMARY_HOST}{static('icon.png')}",
                    "site_icon_width": "1000",
                    "site_icon_height": "1000",
                }
            )
        return result
    else:
        return {
            "community": None,
            "community_identifier": None,
            "community_nav_links": [],
            "site_name": settings.SITE_NAME,
            "site_slogan": settings.SITE_SLOGAN,
            "site_description": settings.SITE_DESCRIPTION,
            "site_icon": f"{settings.PROTOCOL}{settings.PRIMARY_HOST}{static('icon.png')}",
            "site_icon_width": "1000",
            "site_icon_height": "1000",
            "site_discord_url": "https://discord.gg/5MbXZvd",
            "site_wiki_url": "https://github.com/risk-of-thunder/R2Wiki/wiki",
        }


def community_site(request):
    return get_community_context(getattr(request, "community", None))


def selectable_communities(request):
    return {
        "selectable_communities": Community.objects.listed().order_by(
            "-aggregated_fields__package_count", "datetime_created"
        )
    }
