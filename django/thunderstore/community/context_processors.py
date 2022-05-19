from django.templatetags.static import static

from thunderstore.community.models.community import Community


def community_site(request):
    if hasattr(request, "community_site") and request.community_site:
        result = {
            "site_name": request.community_site.site.name,
            "site_slogan": request.community_site.slogan or "",
            "site_description": request.community_site.description or "",
            "site_discord_url": request.community_site.community.discord_url or "",
            "site_wiki_url": request.community_site.community.wiki_url or "",
        }
        if request.community_site.icon:
            url = request.community_site.icon.url
            if not (url.startswith("http://") or url.startswith("https://")):
                url = f"{request.scheme}://{request.get_host()}{url}"
            result.update(
                {
                    "site_icon": url,
                    "site_icon_width": request.community_site.icon_width,
                    "site_icon_height": request.community_site.icon_height,
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
            "site_name": "Thunderstore",
            "site_slogan": "The Risk of Rain 2 Mod Database",
            "site_description": "Thunderstore is a mod database and API for downloading Risk of Rain 2 mods",
            "site_icon": f"{request.scheme}://{request.get_host()}{static('icon.png')}",
            "site_icon_width": "1000",
            "site_icon_height": "1000",
            "site_discord_url": "https://discord.gg/5MbXZvd",
            "site_wiki_url": "https://github.com/risk-of-thunder/R2Wiki/wiki",
        }


def selectable_communities(request):
    return {"selectable_communities": Community.objects.exclude(is_listed=False)}
