from io import BytesIO
from typing import Dict, List, Tuple

from django.conf import settings
from django.db.models import F
from django.shortcuts import redirect
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from rest_framework.exceptions import APIException
from rest_framework.renderers import JSONRenderer
from rest_framework.views import APIView
from sentry_sdk import capture_exception

from thunderstore.repository.models import (
    APIExperimentalPackageIndexCache,
    PackageVersion,
    PackageVersionQuerySet,
)


class ServiceUnavailable(APIException):
    status_code = 503
    default_detail = "Service temporarily unavailable, try again later."
    default_code = "service_unavailable"


class PackageIndexEntry(serializers.Serializer):
    # Many fields have been excluded from this serializer as a design choice
    # to discourage API client design that's not future proof.

    namespace = serializers.CharField()
    name = serializers.CharField()
    version_number = serializers.CharField()

    file_format = serializers.CharField(source="format_spec")
    file_size = serializers.IntegerField()

    dependencies = serializers.SerializerMethodField()

    def get_dependencies(self, instance: PackageVersion) -> List[str]:
        name_map = self.context["dependency_names"]
        adjacency = self.context["dependency_ids"]
        return [name_map[to_id] for to_id in adjacency.get(instance.id, [])]


def _build_dependency_maps() -> Tuple[Dict[int, str], Dict[int, List[int]]]:
    names = {
        version_id: f"{owner}-{name}-{version}"
        for version_id, owner, name, version in PackageVersion.objects.values_list(
            "id",
            "package__owner__name",
            "package__name",
            "version_number",
        )
    }
    adjacency: Dict[int, List[int]] = {}
    # Deterministic order keeps the published index stable. The M2M has none.
    edges = PackageVersion.dependencies.through.objects.order_by(
        "to_packageversion_id"
    ).values_list("from_packageversion_id", "to_packageversion_id")
    for from_id, to_id in edges.iterator():
        adjacency.setdefault(from_id, []).append(to_id)
    return names, adjacency


def serialize_package_index() -> bytes:
    versions: PackageVersionQuerySet = PackageVersion.objects.active().annotate(
        namespace=F("package__namespace")
    )
    dependency_names, dependency_ids = _build_dependency_maps()
    context = {
        "dependency_names": dependency_names,
        "dependency_ids": dependency_ids,
    }
    renderer = JSONRenderer()
    result = BytesIO()

    for entry in versions.chunked_enumerate():
        data = PackageIndexEntry(instance=entry, context=context).data
        result.write(renderer.render(data))
        result.write(b"\n")

    return result.getvalue()


def update_api_experimental_package_index() -> None:
    """Called periodically by a Celery background task"""
    try:
        APIExperimentalPackageIndexCache.update(content=serialize_package_index())
    except Exception as e:  # pragma: no cover
        capture_exception(e)
    APIExperimentalPackageIndexCache.drop_stale_cache()


HOSTNAME = f"{settings.PROTOCOL}{settings.PRIMARY_HOST}"
DESCRIPTION = (
    "Response is a stream of newline delimited JSON.\n\n"
    "Download links are not included in the response. The client is expected to "
    "build them using the following pattern: "
    f"{HOSTNAME}/package/download/{{namespace}}/{{name}}/{{version_number}}/"
)


class PackageIndexApiView(APIView):
    """
    Lists all known package versions across all communities in a stream of
    newline delimited JSON.
    """

    @swagger_auto_schema(
        tags=["experimental"],
        responses={200: PackageIndexEntry(many=True)},
        operation_id="experimental.package-index",
        operation_description=DESCRIPTION,
    )
    def get(self, request):
        cache = APIExperimentalPackageIndexCache.get_latest()
        if not cache:
            raise ServiceUnavailable("Package index not yet built, try again later")
        return redirect(self.request.build_absolute_uri(cache.data.url))
