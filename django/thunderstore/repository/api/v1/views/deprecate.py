from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from thunderstore.core.jwt_helpers import JWTApiView
from thunderstore.core.types import HttpRequestType
from thunderstore.repository.models import DiscordUserBotPermission
from thunderstore.repository.package_reference import PackageReference


class DeprecateModApiView(JWTApiView):
    """
    Deprecates a mod by its package name

    * Requires JWT authentication.
    * Only users with special permissions may use this action
    """

    permission_classes = [AllowAny]

    def get_package(self, package_name):
        if package_name is None:
            raise NotFound()
        reference = PackageReference.parse(package_name)
        if not reference.instance:
            raise NotFound()
        return reference.instance

    def validate_permissions(self):
        discord_user = self.request.decoded.get("user")

        if not discord_user:
            raise PermissionDenied("Insufficient Discord user permissions")

        permissions = DiscordUserBotPermission.objects.filter(
            discord_user_id=discord_user,
            thunderstore_user=self.request.user,
        ).first()

        if not permissions:
            raise PermissionDenied("Insufficient Discord user permissions")

        if not permissions.can_deprecate:
            raise PermissionDenied("Insufficient Discord user permissions")

    @swagger_auto_schema(tags=["v1"])
    def post(
        self,
        request: HttpRequestType,
    ) -> Response:
        package = self.get_package(request.decoded.get("package"))

        if not request.user.has_perm("repository.change_package"):
            raise PermissionDenied()

        self.validate_permissions()

        package.is_deprecated = True
        package.save()

        return Response({"success": True})
