from typing import Optional

from django.http import Http404
from rest_framework import serializers
from rest_framework.generics import RetrieveAPIView, get_object_or_404

from thunderstore.api.utils import CyberstormAutoSchemaMixin
from thunderstore.markdown.templatetags.markdownify import render_markdown
from thunderstore.repository.models import Package, PackageVersion


class CyberstormMarkdownResponseSerializer(serializers.Serializer):
    html = serializers.CharField()


class PackageVersionReadmeAPIView(CyberstormAutoSchemaMixin, RetrieveAPIView):
    """
    Return README.md prerendered as HTML.

    If no version number is provided, the latest version is used.
    """

    serializer_class = CyberstormMarkdownResponseSerializer

    def get_object(self):
        package_version = get_package_version(
            namespace_id=self.kwargs["namespace_id"],
            package_name=self.kwargs["package_name"],
            version_number=self.kwargs.get("version_number"),
        )

        return {"html": render_markdown(package_version.readme)}


class PackageVersionChangelogAPIView(CyberstormAutoSchemaMixin, RetrieveAPIView):
    """
    Return CHANGELOG.md prerendered as HTML.

    If no version number is provided, the latest version is used.
    """

    serializer_class = CyberstormMarkdownResponseSerializer

    def get_object(self):
        package_version = get_package_version(
            namespace_id=self.kwargs["namespace_id"],
            package_name=self.kwargs["package_name"],
            version_number=self.kwargs.get("version_number"),
        )

        if package_version.changelog is None:
            raise Http404

        return {"html": render_markdown(package_version.changelog)}


def get_package_version(
    namespace_id: str,
    package_name: str,
    version_number: Optional[str],
) -> PackageVersion:
    package = get_object_or_404(
        Package.objects.active().select_related("latest"),
        namespace__name=namespace_id,
        name=package_name,
    )

    if version_number:
        return get_object_or_404(
            package.versions.active(),
            version_number=version_number,
        )

    if package.latest.is_active:
        return package.latest

    raise Http404
