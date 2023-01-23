from typing import TYPE_CHECKING, Optional

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse

from thunderstore.community.utils import get_community_site_for_request
from thunderstore.core.urls import AUTH_ROOT

if TYPE_CHECKING:
    from thunderstore.community.models import Community, CommunitySite


class CommunityHttpRequest(HttpRequest):
    community_site: "Optional[CommunitySite]"
    site: "Optional[Site]"
    community: "Optional[Community]"


def add_community_context_to_request(request: CommunityHttpRequest):
    request.site = None
    request.community = None
    try:
        community_site = get_community_site_for_request(request)
    except ObjectDoesNotExist:
        raise Http404
    if not community_site:
        raise Http404
    request.site = community_site.site
    request.community = community_site.community


class CommunitySiteMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.admin_path = reverse("admin:index")
        self.auth_path = f"/{AUTH_ROOT}"

    def get_404(self, request: CommunityHttpRequest) -> HttpResponse:
        main_site_domain = settings.PRIMARY_HOST
        if main_site_domain is not None and main_site_domain != request.get_host():
            # TODO: Replace with unified URL building utility
            main_site_url = f"{settings.PROTOCOL}{main_site_domain}/"
            return HttpResponseRedirect(redirect_to=main_site_url)
        return HttpResponse(content=b"Community not found", status=404)

    def __call__(self, request: CommunityHttpRequest) -> HttpResponse:
        request.site = None
        request.community = None
        request_host = request.META["HTTP_HOST"]
        if (
            settings.AUTH_EXCLUSIVE_HOST
            and request_host == settings.AUTH_EXCLUSIVE_HOST
        ):
            if not request.path.startswith(self.auth_path):
                return self.get_404(request)
        elif not request.path.startswith(self.admin_path):
            try:
                add_community_context_to_request(request)
            except Http404:
                return self.get_404(request)
        return self.get_response(request)
