from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from thunderstore.api.cyberstorm.serializers import (
    ModeratorNoteCreateSerializer,
    ModeratorNoteListSerializer,
    ModeratorNoteSerializer,
    ModeratorNoteUpdateSerializer,
)
from thunderstore.api.cyberstorm.services.moderator_note import (
    create_community_moderator_note,
    create_listing_moderator_note,
    create_version_moderator_note,
    delete_moderator_note,
    list_community_moderator_notes,
    list_listing_moderator_notes,
    list_version_moderator_notes,
    update_moderator_note,
)
from thunderstore.api.cyberstorm.views.package_listing_actions import (
    get_package_listing,
)
from thunderstore.api.utils import conditional_swagger_auto_schema
from thunderstore.community.models import Community, ModeratorNote


def _notes_response(notes) -> Response:
    """All of a resource's notes, wrapped so the body is always valid JSON."""
    data = ModeratorNoteSerializer(notes, many=True).data
    return Response({"moderator_notes": data}, status=status.HTTP_200_OK)


class CommunityModeratorNoteAPIView(APIView):
    """Read (incl. inactive) or create the community's moderator note. Moderators only."""

    permission_classes = [IsAuthenticated]
    serializer_class = ModeratorNoteCreateSerializer

    def get_community(self, kwargs) -> Community:
        return get_object_or_404(Community, identifier=kwargs["community_id"])

    @conditional_swagger_auto_schema(
        operation_id="cyberstorm.community.moderator_note.read",
        responses={200: ModeratorNoteListSerializer},
        tags=["cyberstorm"],
    )
    def get(self, request, *args, **kwargs) -> Response:
        community = self.get_community(kwargs)
        notes = list_community_moderator_notes(agent=request.user, community=community)
        return _notes_response(notes)

    @conditional_swagger_auto_schema(
        operation_id="cyberstorm.community.moderator_note.create",
        request_body=serializer_class,
        responses={201: ModeratorNoteSerializer},
        tags=["cyberstorm"],
    )
    def post(self, request, *args, **kwargs) -> Response:
        community = self.get_community(kwargs)

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        note = create_community_moderator_note(
            agent=request.user,
            community=community,
            content=serializer.validated_data["content"],
        )
        return Response(
            ModeratorNoteSerializer(note).data, status=status.HTTP_201_CREATED
        )


class ListingModeratorNoteAPIView(APIView):
    """Read (incl. inactive) or create the listing-wide moderator note. Moderators only."""

    permission_classes = [IsAuthenticated]
    serializer_class = ModeratorNoteCreateSerializer

    def get_listing(self, kwargs):
        return get_package_listing(
            namespace_id=kwargs["namespace_id"],
            package_name=kwargs["package_name"],
            community_id=kwargs["community_id"],
        )

    @conditional_swagger_auto_schema(
        operation_id="cyberstorm.listing.moderator_note.read",
        responses={200: ModeratorNoteListSerializer},
        tags=["cyberstorm"],
    )
    def get(self, request, *args, **kwargs) -> Response:
        listing = self.get_listing(kwargs)
        notes = list_listing_moderator_notes(agent=request.user, listing=listing)
        return _notes_response(notes)

    @conditional_swagger_auto_schema(
        operation_id="cyberstorm.listing.moderator_note.create",
        request_body=serializer_class,
        responses={201: ModeratorNoteSerializer},
        tags=["cyberstorm"],
    )
    def post(self, request, *args, **kwargs) -> Response:
        listing = self.get_listing(kwargs)

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        note = create_listing_moderator_note(
            agent=request.user,
            listing=listing,
            content=serializer.validated_data["content"],
        )
        return Response(
            ModeratorNoteSerializer(note).data, status=status.HTTP_201_CREATED
        )


class VersionModeratorNoteAPIView(APIView):
    """Read (incl. inactive) or create a package version's moderator note. Moderators only."""

    permission_classes = [IsAuthenticated]
    serializer_class = ModeratorNoteCreateSerializer

    def get_listing_and_version(self, kwargs):
        listing = get_package_listing(
            namespace_id=kwargs["namespace_id"],
            package_name=kwargs["package_name"],
            community_id=kwargs["community_id"],
        )
        version = get_object_or_404(
            listing.package.versions.active(),
            version_number=kwargs["version_number"],
        )
        return listing, version

    @conditional_swagger_auto_schema(
        operation_id="cyberstorm.version.moderator_note.read",
        responses={200: ModeratorNoteListSerializer},
        tags=["cyberstorm"],
    )
    def get(self, request, *args, **kwargs) -> Response:
        listing, version = self.get_listing_and_version(kwargs)
        notes = list_version_moderator_notes(
            agent=request.user, listing=listing, version=version
        )
        return _notes_response(notes)

    @conditional_swagger_auto_schema(
        operation_id="cyberstorm.version.moderator_note.create",
        request_body=serializer_class,
        responses={201: ModeratorNoteSerializer},
        tags=["cyberstorm"],
    )
    def post(self, request, *args, **kwargs) -> Response:
        listing, version = self.get_listing_and_version(kwargs)

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        note = create_version_moderator_note(
            agent=request.user,
            listing=listing,
            version=version,
            content=serializer.validated_data["content"],
        )
        return Response(
            ModeratorNoteSerializer(note).data, status=status.HTTP_201_CREATED
        )


class ModeratorNoteDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ModeratorNoteUpdateSerializer

    @conditional_swagger_auto_schema(
        operation_id="cyberstorm.moderator_note.update",
        request_body=serializer_class,
        responses={200: ModeratorNoteSerializer},
        tags=["cyberstorm"],
    )
    def patch(self, request, *args, **kwargs) -> Response:
        note = get_object_or_404(ModeratorNote, pk=kwargs["note_id"])

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        note = update_moderator_note(
            agent=request.user,
            note=note,
            content=serializer.validated_data.get("content"),
            is_active=serializer.validated_data.get("is_active"),
        )
        return Response(ModeratorNoteSerializer(note).data, status=status.HTTP_200_OK)

    @conditional_swagger_auto_schema(
        operation_id="cyberstorm.moderator_note.delete",
        request_body=None,
        responses={204: "No Content"},
        tags=["cyberstorm"],
    )
    def delete(self, request, *args, **kwargs) -> Response:
        note = get_object_or_404(ModeratorNote, pk=kwargs["note_id"])
        delete_moderator_note(agent=request.user, note=note)
        return Response(status=status.HTTP_204_NO_CONTENT)
