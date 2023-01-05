from django.conf import settings
from django.db.models import Count
from django.templatetags.static import static

from thunderstore.community.models.community import Community


def community_site(request):
    if hasattr(request, "community") and request.community:
        community = request.community
        result = {
            "site_name": settings.SITE_NAME,
            "site_slogan": community.slogan or "",
            "site_description": community.description or "",
            "site_discord_url": community.discord_url or "",
            "site_wiki_url": community.wiki_url or "",
        }
        if community.icon:
            url = community.icon.url
            if not (url.startswith("http://") or url.startswith("https://")):
                url = f"{request.scheme}://{request.get_host()}{url}"
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
                    "site_icon": f"{request.scheme}://{request.get_host()}{static('icon.png')}",
                    "site_icon_width": "1000",
                    "site_icon_height": "1000",
                }
            )
        return result
    else:
        return {
            "site_name": settings.SITE_NAME,
            "site_slogan": settings.SITE_SLOGAN,
            "site_description": settings.SITE_DESCRIPTION,
            "site_icon": f"{request.scheme}://{request.get_host()}{static('icon.png')}",
            "site_icon_width": "1000",
            "site_icon_height": "1000",
            "site_discord_url": "https://discord.gg/5MbXZvd",
            "site_wiki_url": "https://github.com/risk-of-thunder/R2Wiki/wiki",
        }


def selectable_communities(request):
    return {
        "selectable_communities": Community.objects.listed()
        .annotate(package_count=Count("package_listings"))
        .order_by("-package_count", "datetime_created")
    }
