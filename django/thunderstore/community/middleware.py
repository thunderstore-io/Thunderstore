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


class CommunityHttpRequest(HttpRequest):
    community_site: "Optional[CommunitySite]"
    site: "Optional[Site]"
    community: "Optional[Community]"


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
        elif not request.path.startswith(self.admin_path):
            try:
                add_community_context_to_request(request)
            except Http404:
                return self.get_404()
        return self.get_response(request)
