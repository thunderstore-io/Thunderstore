from django.db.models import Count, QuerySet, Sum
from django.http import Http404, HttpRequest, HttpResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.community.models import PackageListing
from thunderstore.community.utils import get_preferred_community
from thunderstore.api.serializers import (
    PackageCategoryCyberstormSerializer,
    PackageDependencyCyberstormSerializer,
    PackageDetailViewContentCyberstormSerializer,
    PackageVersionCyberstormSerializer,
    PackageTeamCyberstormSerializer,
)


class PackageAPIView(APIView):
    permission_classes = []

    @swagger_auto_schema(
        responses={200: PackageDetailViewContentCyberstormSerializer()},
        operation_id="api.package",
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
                "package__latest__dependencies__package__community_listings__community",
                "package__latest__dependencies__package__namespace",
            )
            .annotate(package_dependant_count=Count("package__latest__dependants"))
            .annotate(package_total_downloads=Sum("package__versions__downloads"))
            .annotate(package_total_rating=Count("package__package_ratings"))
        )

    def serialize_results(
        self, listing: PackageListing
    ) -> PackageDetailViewContentCyberstormSerializer:
        """
        Format results to transportation.
        """
        latest = listing.package.latest
        latest.package = listing.package  # To avoid extra DB hits

        dependencies = []
        for d in latest.dependencies.all():
            community = get_preferred_community(d.package, listing.community)

            dependencies.append(
                PackageDependencyCyberstormSerializer(
                    {
                        "name": d.name,
                        "namespace": d.package.namespace.name,
                        "community": community.identifier
                        if community
                        else None,
                        "shortDescription": d.description,
                        "imageSource": d.icon.url if bool(d.icon) else None,
                        "version": d.version_number,
                    }
                ).data
            )

        return PackageDetailViewContentCyberstormSerializer(
            {
                "name": listing.package.name,
                "namespace": listing.package.namespace.name,
                "community": listing.community.identifier,
                "shortDescription": latest.description,
                "imageSource": latest.icon.url if bool(latest.icon) else None,
                "downloadCount": listing.package_total_downloads,
                "likes": listing.package_total_rating,
                "size": latest.file_size,
                "author": listing.package.owner.name,
                "lastUpdated": listing.package.date_updated,
                "isPinned": listing.package.is_pinned,
                "isNsfw": listing.has_nsfw_content,
                "isDeprecated": listing.package.is_deprecated,
                "categories": [PackageCategoryCyberstormSerializer(c).data for c in listing.categories.all()],
                # PackageCard information above 
                "description": latest.readme,
                #TODO: We do not have support for additional images yet
                "additionalImages": None,
                "gitHubLink": latest.website_url,
                "donationLink": listing.package.owner.donation_link,
                "firstUploaded": listing.package.date_created,
                "dependencyString": latest.full_version_name,
                "dependencies": dependencies,
                "dependantCount": listing.package_dependant_count,
                "team": PackageTeamCyberstormSerializer(
                    {
                        "name": listing.package.owner.name,
                        "members": [
                            {
                                "user": member.username,
                                # TODO: We don't have user profile pics yet
                                "imageSource": None,
                                "role": member.role,
                            }
                        for member in listing.package.owner.members.all()
                        ]
                    }
                ).data,
                "versions": [
                    PackageVersionCyberstormSerializer(
                        {
                            "uploadDate": v.date_created,
                            "downloadCount": v.downloads,
                            "version": v.version_number,
                            "changelog": v.changelog,
                        }
                    ).data
                    for v in listing.package.available_versions
                ],
            }
        )
