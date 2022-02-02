import re
from collections import namedtuple
from typing import TYPE_CHECKING, Optional

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse

from thunderstore.community.utils import get_community_site_for_request
from thunderstore.core.urls import AUTH_ROOT
from thunderstore.core.utils import make_full_url

if TYPE_CHECKING:
    from thunderstore.community.models import Community, CommunitySite

OLD_URL_REGEXS = [
    ("packages.download", "/package/download/([^/]*?)/([^/]*?)/([^/]*?)/$", 3),
    ("packages.list_by_dependency", "/package/([^/]*?)/([^/]*?)/dependants/$", 2),
    ("packages.version.detail", "/package/([^/]*?)/([^/]*?)/([^/]*?)/$", 3),
    ("packages.detail", "/package/([^/]*?)/([^/]*?)/$", 2),
    ("packages.list_by_owner", "/package/([^/]*?)/$", 1),
]


class CommunityHttpRequest(HttpRequest):
    community_site: "Optional[CommunitySite]"
    site: "Optional[Site]"
    community: "Optional[Community]"


def solve_redirect(path, community_identifier):
    for reverse_name, regex, kwarg_amount in OLD_URL_REGEXS:
        result = re.search(regex, path)
        if result:
            kwargs = {"community_identifier": community_identifier}
            kwargs.update({"owner": result.group(1)})
            if kwarg_amount > 1:
                kwargs.update({"name": result.group(2)})
            if kwarg_amount > 2:
                kwargs.update({"version": result.group(3)})
            return HttpResponseRedirect(reverse(reverse_name, kwargs=kwargs))
    return None


def add_community_context_to_request(request: CommunityHttpRequest):
    request.community_site = None
    request.site = None
    request.community = None
    try:
        community_site = get_community_site_for_request(request)
    except ObjectDoesNotExist:
        raise Http404
    if not community_site:
        raise Http404
    request.community_site = community_site
    request.site = community_site.site
    request.community = community_site.community


class CommunitySiteMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.admin_path = reverse("admin:index")
        self.auth_path = f"/{AUTH_ROOT}"

    def get_404(self) -> HttpResponse:
        return HttpResponse(content=b"Community not found", status=404)

    def __call__(self, request: CommunityHttpRequest) -> HttpResponse:
        request.community_site = None
        request.site = None
        request.community = None
        request_host = request.META["HTTP_HOST"]
        if (
            settings.AUTH_EXCLUSIVE_HOST
            and request_host == settings.AUTH_EXCLUSIVE_HOST
        ):
            if not request.path.startswith(self.auth_path):
                return self.get_404()

        elif request.path.startswith("/package/"):
            # Remove this later, when request.community_site is removed
            try:
                add_community_context_to_request(request)
            except Http404:
                return self.get_404()
            # Remove above later, when request.community_site is removed

            # Resolve community
            split_host = request.META["HTTP_HOST"].split(".")
            if len(split_host) < 3:
                community_identifier = "riskofrain2"
            elif len(split_host) < 4:
                community_identifier = split_host[0]
            else:
                return self.get_404()

            redirect_to = solve_redirect(request.path, community_identifier)
            if redirect_to is None:
                return self.get_404()
            else:
                return redirect_to

        elif len(request.META["HTTP_HOST"].split(".")) > 2:
            if request.path.startswith("/c/"):
                # Remove this later, when request.community_site is removed
                try:
                    add_community_context_to_request(request)
                except Http404:
                    return self.get_404()
                # Remove above later, when request.community_site is removed

                splitted_host = request.META["HTTP_HOST"].split(".")

                if len(splitted_host) < 4 and request.path.startswith(
                    f"/c/{splitted_host[0]}/"
                ):
                    request.META[
                        "HTTP_HOST"
                    ] = f"{splitted_host[-2]}.{splitted_host[-1]}"
                    return HttpResponseRedirect(make_full_url(request))
            else:
                return self.get_404()

        elif not request.path.startswith(self.admin_path):
            try:
                add_community_context_to_request(request)
            except Http404:
                return self.get_404()
        return self.get_response(request)
