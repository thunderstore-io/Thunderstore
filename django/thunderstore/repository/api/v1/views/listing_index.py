from django.shortcuts import get_object_or_404, redirect
from drf_yasg.utils import swagger_auto_schema  # type: ignore
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.community.models import Community
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
            Community.objects.listed(),
            identifier=community_identifier,
        )
        cache = APIV1ChunkedPackageCache.get_latest_for_community(community)

        if cache:
            return redirect(request.build_absolute_uri(cache.index.data_url))

        return Response({"error": "No cache available"}, status=503)
