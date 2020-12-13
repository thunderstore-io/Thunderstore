from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.urls import reverse

from thunderstore.community.utils import get_community_site_for_request


def add_community_context_to_request(request):
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

    def __call__(self, request):
        request.community_site = None
        request.site = None
        request.community = None
        if not request.path.startswith(reverse("admin:index")):
            add_community_context_to_request(request)
        return self.get_response(request)
