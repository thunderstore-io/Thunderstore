from drf_yasg.utils import swagger_auto_schema
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.repository.api.experimental.serializers import (
    PackageUploadSerializerExperiemental,
    PackageVersionSerializerExperimental,
)
from thunderstore.repository.package_upload import MAX_PACKAGE_SIZE


class UploadPackageApiView(APIView):
    """
    Uploads a package. Requires multipart/form-data.
    """

    parser_classes = [MultiPartParser]

    @swagger_auto_schema(
        deprecated=True,
        tags=["experimental"],
    )
    def get(self, request):
        return Response({"max_package_size_bytes": MAX_PACKAGE_SIZE})

    @swagger_auto_schema(
        deprecated=True,
        tags=["experimental"],
    )
    def post(self, request):
        serializer = PackageUploadSerializerExperiemental(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        package_version = serializer.save()
        serializer = PackageVersionSerializerExperimental(
            instance=package_version,
            context={"request": request},
        )
        return Response(serializer.data)
