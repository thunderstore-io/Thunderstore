from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, serializers
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.repository.api.experimental.serializers import (
    PackageSubmissionMetadataSerializer,
    PackageSubmissionResult,
)
from thunderstore.repository.api.experimental.views.submit import get_usermedia_or_404
from thunderstore.repository.models.submission import AsyncPackageSubmission


class PackageSubmissionStatusSerializer(serializers.Serializer):
    id = serializers.CharField()
    status = serializers.CharField()
    form_errors = serializers.JSONField(required=False)
    task_error = serializers.BooleanField()
    result = serializers.SerializerMethodField(required=False)

    def get_result(self, instance: AsyncPackageSubmission):
        if not instance.created_version:
            return None

        listings = instance.created_version.package.community_listings.active()
        available_communities = []
        for listing in listings:
            available_communities.append(
                {
                    "community": listing.community,
                    "categories": listing.categories.all(),
                    "url": listing.get_full_url(),
                }
            )

        return PackageSubmissionResult(
            instance={
                "package_version": instance.created_version,
                "available_communities": available_communities,
            },
        ).data


class CreateAsyncPackageSubmissionApiView(APIView):
    """
    Submits a pre-uploaded package by upload uuid asynchronously.
    """

    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        request_body=PackageSubmissionMetadataSerializer(),
        responses={200: PackageSubmissionStatusSerializer()},
        operation_id="experimental.package.submit-async",
        tags=["experimental"],
    )
    def post(self, request):
        serializer = PackageSubmissionMetadataSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        # This will raise an API error if the upload doesn't exist, which is
        # nicer than a DB integrity error.
        get_usermedia_or_404(
            self.request.user, serializer.validated_data["upload_uuid"]
        )

        submission: AsyncPackageSubmission = AsyncPackageSubmission.objects.create(
            owner=request.user,
            file_id=serializer.validated_data["upload_uuid"],
            form_data=PackageSubmissionMetadataSerializer(
                serializer.validated_data
            ).data,
        )
        submission.schedule_if_appropriate()
        response_serializer = PackageSubmissionStatusSerializer(instance=submission)
        return Response(response_serializer.data)


class PollSubmissionStatusApiView(APIView):
    """
    Polls the status of an async package submission by its ID.
    """

    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        responses={200: PackageSubmissionResult()},
        operation_id="experimental.package.submit-async.poll",
        tags=["experimental"],
    )
    def get(self, request, submission_id: str):
        submission = get_object_or_404(
            AsyncPackageSubmission,
            pk=submission_id,
            owner=request.user,
        )
        submission.schedule_if_appropriate()
        serializer = PackageSubmissionStatusSerializer(
            instance=submission,
        )
        return Response(serializer.data)
