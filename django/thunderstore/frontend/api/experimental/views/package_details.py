from django.core.exceptions import PermissionDenied
from django.db.models import Count, QuerySet, Sum
from django.http import HttpRequest, HttpResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.community.models import PackageListing
from thunderstore.community.utils import get_preferred_community
from thunderstore.frontend.api.experimental.serializers.views import (
    PackageCategorySerializer,
    PackageDependencySerializer,
    PackageDetailViewContentSerializer,
    PackageVersionSerializer,
)


class PackageDetailApiView(APIView):
    """
    Return details about a single Package.
    """

    permission_classes = []

    @swagger_auto_schema(
        responses={200: PackageDetailViewContentSerializer()},
        operation_id="experimental.frontend.community.package",
    )
    def get(
        self,
        request: HttpRequest,
        community_identifier: str,
        package_namespace: str,
        package_name: str,
    ) -> HttpResponse:
        listing = get_object_or_404(
            self.get_listing_queryset(),
            community__identifier=community_identifier,
            community__is_listed=True,
            package__namespace__name=package_namespace,
            package__name=package_name,
        )

        if not listing.can_be_viewed_by_user(request.user):
            raise PermissionDenied()

        serializer = self.serialize_results(listing)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_listing_queryset(self) -> QuerySet[PackageListing]:
        """
        NOTE: this does not fetch package's versions, they're fetched
        separately in serialize_results to use existing method to sort
        results by version number.
        """
        return (
            PackageListing.objects.active()
            .select_related(
                "package",
                "package__latest",
                "package__namespace",
                "package__owner",
            )
            .prefetch_related(
                "categories",
                "community__sites",
                "package__latest__dependencies__package__community_listings__community",
                "package__latest__dependencies__package__namespace",
            )
            .annotate(package_dependant_count=Count("package__latest__dependants"))
            .annotate(package_total_downloads=Sum("package__versions__downloads"))
            .annotate(package_total_rating=Count("package__package_ratings"))
        )

    def serialize_results(
        self, listing: PackageListing
    ) -> PackageDetailViewContentSerializer:
        """
        Format results to transportation.
        """
        latest = listing.package.latest
        latest.package = listing.package  # To avoid extra DB hits

        dependencies = []
        for d in latest.dependencies.all():
            community = get_preferred_community(d.package, listing.community)

            dependencies.append(
                PackageDependencySerializer(
                    {
                        "community_name": community.name if community else None,
                        "community_identifier": community.identifier
                        if community
                        else None,
                        "description": d.description,
                        "image_src": d.icon.url if bool(d.icon) else None,
                        "namespace": d.package.namespace.name,
                        "package_name": d.name,
                        "version_number": d.version_number,
                    }
                ).data
            )

        return PackageDetailViewContentSerializer(
            {
                "bg_image_src": listing.community.site_image_url,
                "categories": [
                    PackageCategorySerializer(c).data for c in listing.categories.all()
                ],
                "community_name": listing.community.name,
                "community_identifier": listing.community.identifier,
                "dependant_count": listing.package_dependant_count,
                "dependencies": dependencies,
                "dependency_string": latest.full_version_name,
                "description": latest.description,
                "download_count": listing.package_total_downloads,
                "download_url": latest.download_url,
                "image_src": latest.icon.url if bool(latest.icon) else None,
                "install_url": latest.get_install_url(self.request),
                "last_updated": listing.package.date_updated,
                "markdown": latest.readme,
                "namespace": listing.package.namespace.name,
                "package_name": listing.package.name,
                "rating_score": listing.package_total_rating,
                "team_name": listing.package.owner.name,
                "versions": [
                    PackageVersionSerializer(
                        {
                            "date_created": v.date_created,
                            "download_count": v.downloads,
                            "download_url": v.download_url,
                            "install_url": v.get_install_url(self.request),
                            "version_number": v.version_number,
                        }
                    ).data
                    for v in listing.package.available_versions
                ],
                "website": latest.website_url,
            }
        )
