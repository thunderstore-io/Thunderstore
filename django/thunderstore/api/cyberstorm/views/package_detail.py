from django.db.models import Count, OuterRef, QuerySet, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.http import Http404, HttpRequest, HttpResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.api.cyberstorm.serializers import (
    CyberstormPackageSerializer,
    CyberstormTeamSerializer,
)
from thunderstore.community.models import PackageListing
from thunderstore.community.utils import get_preferred_community
from thunderstore.repository.models.package import Package


class PackageListingDetailAPIView(APIView):
    permission_classes = []

    @swagger_auto_schema(
        responses={200: CyberstormPackageSerializer()},
        operation_id="cyberstorm.package",
    )
    def get(
        self,
        request: HttpRequest,
        community_id: str,
        package_namespace: str,
        package_name: str,
    ) -> HttpResponse:
        listing = get_object_or_404(
            self.get_listing_queryset(),
            community__identifier=community_id,
            community__is_listed=True,
            package__namespace__name=package_namespace,
            package__name=package_name,
        )

        if not listing.can_be_viewed_by_user(request.user):
            raise Http404()

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
                "package__owner__members",
                "package__latest__dependencies__package__community_listings__community",
                "package__latest__dependencies__package__namespace",
            )
            .annotate(package_dependant_count=Count("package__latest__dependencies"))
            .annotate(
                package_total_downloads=Coalesce(
                    Subquery(
                        Package.objects.filter(pk=OuterRef("package__pk")).values(
                            downloads=Sum("versions__downloads")
                        )[:1]
                    ),
                    Value(0),
                )
            )
            .annotate(
                package_total_rating=Count("package__package_ratings", distinct=True)
            )
        )

    def serialize_results(self, listing: PackageListing) -> CyberstormPackageSerializer:
        """
        Format results to transportation.
        """
        latest = listing.package.latest
        latest.package = listing.package  # To avoid extra DB hits

        dependencies = []
        for d in latest.dependencies.all():
            community = get_preferred_community(d.package, listing.community)

            dependencies.append(
                PackageDependencySerializerCyberstorm(
                    {
                        "name": d.name,
                        "namespace": d.package.namespace.name,
                        "community": community.identifier if community else None,
                        "short_description": d.description,
                        "image_source": d.icon.url if bool(d.icon) else None,
                        "version": d.version_number,
                    }
                ).data
            )

        return CyberstormPackageSerializer(
            {
                "dependency_string": latest.full_version_name,
                "dependencies": dependencies,
                "dependant_count": listing.package_dependant_count,
                "team": CyberstormTeamSerializer(listing.package.owner).data,
            }
        )
