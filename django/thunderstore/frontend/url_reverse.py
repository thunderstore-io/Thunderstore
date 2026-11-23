from typing import Dict, Optional

from thunderstore.community.consts import DEFAULT_COMMUNITY_IDENTIFIER
from thunderstore.community.models import Community


def get_community_url_reverse_args(
    community: Optional[Community],
    viewname: str,
    kwargs: Optional[Dict] = None,
) -> Dict:
    # Old urls dont have a community identifier so we resolve them to the default one.
    is_default = (
        community is None or community.identifier == DEFAULT_COMMUNITY_IDENTIFIER
    )
    if is_default and Community.should_use_old_urls(community):
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
