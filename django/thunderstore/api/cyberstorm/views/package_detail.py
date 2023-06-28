from django.db.models import Count, OuterRef, QuerySet, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.http import Http404, HttpRequest, HttpResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.api.cyberstorm.serializers import (
    PackageCategorySerializerCyberstorm,
    PackageDependencySerializerCyberstorm,
    PackageDetailSerializerCyberstorm,
    PackageTeamSerializerCyberstorm,
    PackageVersionSerializerCyberstorm,
)
from thunderstore.community.models import PackageListing
from thunderstore.community.utils import get_preferred_community
from thunderstore.repository.models.package import Package


class PackageDetailAPIView(APIView):
    permission_classes = []

    @swagger_auto_schema(
        responses={200: PackageDetailSerializerCyberstorm()},
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

    def serialize_results(
        self, listing: PackageListing
    ) -> PackageDetailSerializerCyberstorm:
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

        return PackageDetailSerializerCyberstorm(
            {
                "name": listing.package.name,
                "namespace": listing.package.namespace.name,
                "community": listing.community.identifier,
                "short_description": latest.description,
                "image_source": latest.icon.url if bool(latest.icon) else None,
                "download_count": listing.package_total_downloads,
                "likes": listing.package_total_rating,
                "size": latest.file_size,
                "author": listing.package.owner.name,
                "last_updated": listing.package.date_updated,
                "is_pinned": listing.package.is_pinned,
                "is_nsfw": listing.has_nsfw_content,
                "is_deprecated": listing.package.is_deprecated,
                "categories": [
                    PackageCategorySerializerCyberstorm(c).data
                    for c in listing.categories.all()
                ],
                "description": latest.readme,
                "github_link": latest.website_url,
                "donation_link": listing.package.owner.donation_link,
                "first_uploaded": listing.package.date_created,
                "dependency_string": latest.full_version_name,
                "dependencies": dependencies,
                "dependant_count": listing.package_dependant_count,
                "team": PackageTeamSerializerCyberstorm(
                    {
                        "name": listing.package.owner.name,
                        "members": [
                            {
                                "user": member.username,
                                # TODO: We don't have user profile pics yet
                                "image_source": None,
                                "role": member.role,
                            }
                            for member in listing.package.owner.members.all()
                        ],
                    }
                ).data,
                "versions": [
                    PackageVersionSerializerCyberstorm(
                        {
                            "upload_date": v.date_created,
                            "download_count": v.downloads,
                            "version": v.version_number,
                            "changelog": v.changelog,
                        }
                    ).data
                    for v in listing.package.available_versions
                ],
            }
        )
