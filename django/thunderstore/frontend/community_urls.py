from typing import Dict, Optional

from thunderstore.community.models import Community


def should_use_old_urls(community: Optional[Community]):
    return not community or community.main_site


def get_community_url_reverse_args(
    community: Optional[Community],
    viewname: str,
    kwargs: Optional[Dict] = None,
) -> Dict:
    if should_use_old_urls(community):
        return {
            "viewname": f"old_urls:{viewname}",
            "kwargs": kwargs,
        }
    else:
        if kwargs is None:
            kwargs = dict()
        kwargs["community_identifier"] = community.identifier
        return {
            "viewname": f"communities:community:{viewname}",
            "kwargs": kwargs,
        }
