from django.db.models import Count, QuerySet
from django.http import Http404, HttpRequest, HttpResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.api.cyberstorm.serializers import (
    PackageTeamSerializerCyberstorm,
    PackageVersionExtendedSerializerCyberstorm,
)
from thunderstore.community.models import PackageListing
from thunderstore.repository.models.package_version import PackageVersion


class PackageVersionDetailAPIView(APIView):
    permission_classes = []

    @swagger_auto_schema(
        responses={200: PackageVersionExtendedSerializerCyberstorm()},
        operation_id="cyberstorm.package.version",
    )
    def get(
        self,
        request: HttpRequest,
        community_id: str,
        package_namespace: str,
        package_name: str,
        package_version: str,
    ) -> HttpResponse:
        listing = get_object_or_404(
            self.get_listing_queryset(),
            community__identifier=community_id,
            community__is_listed=True,
            package__namespace__name=package_namespace,
            package__name=package_name,
        )
        version = get_object_or_404(
            listing.package.versions.active(), version_number=package_version
        )

        if not listing.can_be_viewed_by_user(request.user):
            raise Http404()

        serializer = self.serialize_results(listing, version)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_listing_queryset(self) -> QuerySet[PackageListing]:
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
            .annotate(
                package_total_rating=Count("package__package_ratings", distinct=True)
            )
        )

    def serialize_results(
        self, listing: PackageListing, version: PackageVersion
    ) -> PackageVersionExtendedSerializerCyberstorm:
        """
        Format results to transportation.
        """
        version.package = listing.package  # To avoid extra DB hits

        return PackageVersionExtendedSerializerCyberstorm(
            {
                "name": listing.package.name,
                "namespace": listing.package.namespace.name,
                "community": listing.community.identifier,
                "short_description": version.description,
                "image_source": version.icon.url if bool(version.icon) else None,
                "download_count": version.downloads,
                "size": version.file_size,
                "author": listing.package.owner.name,
                "is_pinned": listing.package.is_pinned,
                "is_nsfw": listing.has_nsfw_content,
                "is_deprecated": listing.package.is_deprecated,
                "description": version.readme,
                "github_link": version.website_url,
                "donation_link": listing.package.owner.donation_link,
                "upload_date": version.date_created,
                "version": version.version_number,
                "changelog": version.changelog,
                "dependency_string": version.full_version_name,
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
            }
        )
