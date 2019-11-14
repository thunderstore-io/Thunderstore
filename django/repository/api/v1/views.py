from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response

from core.jwt_helpers import JWTApiView
from repository.models import Package, DiscordUserBotPermission


class DeprecateModApiView(JWTApiView):
    """
    Deprecates a mod by it's package name

    * Requires JWT authentication.
    * Only users with special permissions may use this action
    """

    def get_package(self, package_name):
        if package_name is None:
            raise NotFound()
        components = package_name.split("-")
        if len(components) != 2:
            raise NotFound()
        package = Package.objects.filter(
            owner__name=components[0],
            name=components[1],
        ).first()
        if not package:
            raise NotFound()
        return package

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

    def post(self, request, format=None):
        package = self.get_package(request.decoded.get("package"))

        if not request.user.has_perm("repository.change_package"):
            raise PermissionDenied()

        self.validate_permissions()

        package.is_deprecated = True
        package.save()

        return Response({"success": True})
