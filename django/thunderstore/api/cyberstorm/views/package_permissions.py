from django.http import HttpRequest
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.api.cyberstorm.serializers import PackagePermissionsSerializer
from thunderstore.api.utils import conditional_swagger_auto_schema
from thunderstore.repository.models import Community, PackageListing
from thunderstore.repository.views.package._utils import get_package_listing_or_404
from thunderstore.repository.views.package.detail import PermissionsChecker


class PackagePermissionsAPIView(APIView):
    """
    View for getting the permissions for the current user on a package.
    """

    permission_classes = [IsAuthenticated]

    def permissions_checker(self, listing) -> PermissionsChecker:
        if not listing or not self.request.user:
            return None
        return PermissionsChecker(listing, self.request.user)

    def get_listing(
        self, namespace_id: str, package_name: str, community: Community
    ) -> PackageListing:
        return get_package_listing_or_404(
            namespace=namespace_id,
            name=package_name,
            community=community,
        )

    def get_permissions_data(
        self, namespace_id: str, package_name: str, community_id: str
    ) -> dict:
        community = get_object_or_404(Community, identifier=community_id)
        listing = self.get_listing(namespace_id, package_name, community)

        permissions_checker = self.permissions_checker(listing)
        if not permissions_checker:
            return {}

        permission_data = permissions_checker.get_permissions()
        return permission_data

    @conditional_swagger_auto_schema(
        responses={200: PackagePermissionsSerializer},
        operation_id="cyberstorm.package.permissions",
        tags=["cyberstorm"],
    )
    def get(
        self,
        request: HttpRequest,
        community_id: str,
        namespace_id: str,
        package_name: str,
    ) -> Response:
        permission_data = self.get_permissions_data(
            namespace_id, package_name, community_id
        )
        if not permission_data:
            return Response(
                {"message": "Permissions not found."}, status=status.HTTP_404_NOT_FOUND
            )

        data = {
            "package": {
                "community_id": community_id,
                "namespace_id": namespace_id,
                "package_name": package_name,
            },
            "permissions": {**permission_data},
        }

        serializer = PackagePermissionsSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)
