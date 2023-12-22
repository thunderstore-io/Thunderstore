from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from thunderstore.community.api.experimental.serializers import (
    PackageListingUpdateRequestSerializer,
    PackageListingUpdateResponseSerializer,
)
from thunderstore.community.models import PackageListing
from thunderstore.repository.views.repository import get_package_listing_or_404


class PackageListingUpdateApiView(GenericAPIView):
    queryset = PackageListing.objects.active().select_related(
        "community",
        "package",
    )
    serializer_class = PackageListingUpdateResponseSerializer

    @swagger_auto_schema(
        operation_id="experimental.package_listing.update",
        request_body=PackageListingUpdateRequestSerializer,
        responses={200: serializer_class()},
        tags=["experimental"],
    )
    def post(self, request, *args, **kwargs):
        listing: PackageListing = self.get_object()
        request_serializer = PackageListingUpdateRequestSerializer(
            data=request.data, context={"community": listing.community}
        )
        request_serializer.is_valid(raise_exception=True)
        if listing.check_update_categories_permission(request.user):
            listing.update_categories(
                agent=request.user,
                categories=request_serializer.validated_data["categories"],
            )
            get_package_listing_or_404.clear_cache_with_args(
                namespace=listing.package.namespace.name,
                name=listing.package.name,
                community=listing.community,
            )
            serializer = self.serializer_class(instance=listing)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            raise PermissionDenied()
