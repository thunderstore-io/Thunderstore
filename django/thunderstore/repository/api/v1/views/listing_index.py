from django.shortcuts import get_object_or_404, redirect
from django.utils.cache import get_conditional_response
from django.utils.http import http_date
from drf_yasg.utils import swagger_auto_schema  # type: ignore
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.community.models import Community
from thunderstore.core.utils import replace_cdn
from thunderstore.repository.models import APIV1ChunkedPackageCache


class PackageListingIndex(APIView):
    """
    Return a blob file containing URLs to package listing chunks.
    Client needs to gunzip and JSON parse the blob contents.

    /c/{community_id}/api/v1/package-listing-index/
    """

    @swagger_auto_schema(
        tags=["api"],
        auto_schema=None,  # Hide from API docs for now.
    )
    def get(self, request: Request, community_identifier: str):
        community = get_object_or_404(
            Community.objects,
            identifier=community_identifier,
        )
        cache = APIV1ChunkedPackageCache.get_latest_for_community(community)

        if not cache:
            return Response({"error": "No cache available"}, status=503)

        last_modified = int(cache.created_at.timestamp())
        response = get_conditional_response(request, last_modified=last_modified)

        if response:
            return response

        url = request.build_absolute_uri(cache.index.data_url)
        url = replace_cdn(url, request.query_params.get("cdn"))
        response = redirect(url)
        response["Last-Modified"] = http_date(last_modified)
        return response
