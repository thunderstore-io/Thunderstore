from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Dict, List, TypedDict

from django.urls import reverse
from django.utils.functional import SimpleLazyObject

from thunderstore.frontend.models import FooterLink, NavLink

if TYPE_CHECKING:
    from typing import NotRequired


def nav_links(request):
    return {
        # This is implicitly ordered based on the model's default ordering,
        # which follows the db index.
        "global_nav_links": NavLink.objects.filter(is_active=True),
    }


class FooterLinkData(TypedDict):
    href: str
    title: str
    css_class: "NotRequired[str | None]"
    target: "NotRequired[str | None]"


class FooterLinkGroup(TypedDict):
    title: str
    links: List[FooterLinkData]


developer_links = [
    {
        "href": reverse("swagger"),
        "title": "API Docs",
    },
    {
        "href": "https://github.com/thunderstore-io/Thunderstore",
        "title": "GitHub Repo",
    },
    {
        "href": reverse("old_urls:packages.create.docs"),
        "title": "Package Format Docs",
    },
    {
        "href": reverse("tools.markdown-preview"),
        "title": "Markdown Preview",
    },
    {
        "href": reverse("tools.manifest-v1-validator"),
        "title": "Manifest Validator",
    },
]


def build_footer_links() -> List[FooterLinkGroup]:
    link_groups: Dict[str, List[FooterLinkData]] = defaultdict(
        list,
        {
            "Developers": list(developer_links),
        },
    )

    # Implicity sorted correctly in the db + we don't care about
    # re-sorting if the `Developers` column is appended as a design
    # choice. Nothing breaks if that choice is changed later, it's
    # just a tiny amount more performant.
    entry: FooterLink
    for entry in FooterLink.objects.filter(is_active=True):
        link_groups[entry.group_title].append(
            {
                "href": entry.href,
                "title": entry.title,
                "css_class": entry.css_class,
                "target": entry.target,
            }
        )

    return sorted(
        [
            {
                "title": key,
                "links": values,
            }
            for key, values in link_groups.items()
        ],
        key=lambda x: x["title"],
    )


def footer_links(request):
    # The template fragment is cached so we should make the context processor
    # return a lazy object to avoid DB queries when re-rendering the template
    # isn't needed.
    result = SimpleLazyObject(build_footer_links)

    return {
        "footer_link_groups": result,
    }
