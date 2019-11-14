from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response

from core.jwt_helpers import JWTApiView
from repository.models import Package


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

    def post(self, request, format=None):
        package = self.get_package(request.decoded.get("package"))

        if not request.user.has_perm("repository.change_package"):
            raise PermissionDenied()

        package.is_deprecated = True
        package.save()

        return Response({"success": True})
