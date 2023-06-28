from django.db.models import BooleanField, Case, Count, Q, Sum, When
from django.http import HttpRequest, HttpResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView, get_object_or_404
from rest_framework.response import Response

from thunderstore.api.cyberstorm.serializers import CommunitySerializerCyberstorm
from thunderstore.community.consts import PackageListingReviewStatus
from thunderstore.community.models import Community


class CommunityDetailAPIView(GenericAPIView):
    permission_classes = []

    @swagger_auto_schema(
        responses={200: CommunitySerializerCyberstorm()},
        operation_id="cyberstorm.community",
    )
    def get(self, request: HttpRequest, community_id: str) -> HttpResponse:
        c_q = Community.objects.annotate(
            pkgs=Count(
                "package_listings",
                filter=Q(
                    Q(package_listings__package__is_deprecated=False)
                    & Q(
                        Case(
                            When(
                                require_package_listing_approval=True,
                                then=Case(
                                    When(
                                        Q(
                                            package_listings__review_status=PackageListingReviewStatus.approved
                                        ),
                                        then=True,
                                    ),
                                    default=False,
                                    output_field=BooleanField(),
                                ),
                            ),
                            default=Case(
                                When(
                                    Q(
                                        package_listings__review_status=PackageListingReviewStatus.unreviewed
                                    )
                                    | Q(
                                        package_listings__review_status=PackageListingReviewStatus.approved
                                    ),
                                    then=True,
                                ),
                                default=False,
                                output_field=BooleanField(),
                            ),
                        ),
                    ),
                ),
                distinct=True,
            ),
            downloads=Sum(
                Case(
                    When(package_listings__package__is_deprecated=True, then=0),
                    When(
                        package_listings__review_status=PackageListingReviewStatus.rejected,
                        then=0,
                    ),
                    default="package_listings__package__versions__downloads",
                )
            ),
        )

        c = get_object_or_404(c_q, identifier=community_id)

        serializer = self.serialize_results(c)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def serialize_results(self, c: Community):
        return CommunitySerializerCyberstorm(
            {
                "name": c.name,
                "identifier": c.identifier,
                "download_count": c.downloads,
                "package_count": c.pkgs,
                "background_image_url": c.background_image_url,
                "description": c.description,
                "discord_link": c.discord_url,
            }
        )
