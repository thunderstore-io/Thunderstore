from typing import Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import QuerySet

from thunderstore.community.models import Community, ModeratorNote, PackageListing
from thunderstore.core.types import UserType
from thunderstore.repository.models import PackageVersion

# CACHING / DATA-LEAK NOTE: moderator notes are exposed only through PUBLIC read
# paths and are byte-identical for every viewer, so they are safe to serve from a
# shared cache. There IS a public cache window to reason about:
#   * The Django listing/version detail endpoint is user-aware and not
#     function-cached, but the listing PAGE is publicly CDN-cached at the frontend
#     SSR layer (cyberstorm-remix wraps the loader with `ssrLoader(..., {cache:
#     true})` and forwards `public, max-age=60, s-maxage=300, swr=600`).
#   * The community detail endpoint is public-cached via PublicCacheMixin (short
#     TTL).
# A note mutation does not modify the PackageListing/Community rows, so there is no
# per-key server cache to invalidate; edits simply surface within those public
# TTLs. This is safe ONLY because notes are public and the cached read is
# anonymous -- NEVER embed a private/non-public field on these read paths, or it
# would be served to everyone from the shared cache.


def list_community_moderator_notes(
    *, agent: UserType, community: Community
) -> "QuerySet[ModeratorNote]":
    """All of the community's notes (active and inactive); moderators only."""
    community.ensure_user_can_moderate_packages(agent)
    return community.moderator_notes.all()


def list_listing_moderator_notes(
    *, agent: UserType, listing: PackageListing
) -> "QuerySet[ModeratorNote]":
    """All listing-wide notes (active and inactive); moderators only."""
    listing.community.ensure_user_can_moderate_packages(agent)
    return listing.moderator_notes.filter(package_version__isnull=True)


def list_version_moderator_notes(
    *, agent: UserType, listing: PackageListing, version: PackageVersion
) -> "QuerySet[ModeratorNote]":
    """All of the version's notes (active and inactive); moderators only."""
    listing.community.ensure_user_can_moderate_packages(agent)
    return listing.moderator_notes.filter(package_version=version)


@transaction.atomic
def create_community_moderator_note(
    *, agent: UserType, community: Community, content: str
) -> ModeratorNote:
    # Multiple active notes may coexist per resource, so creation never touches
    # other notes.
    community.ensure_user_can_moderate_packages(agent)
    return ModeratorNote.objects.create(
        community=community,
        author=agent,
        content=content,
    )


@transaction.atomic
def create_listing_moderator_note(
    *, agent: UserType, listing: PackageListing, content: str
) -> ModeratorNote:
    listing.community.ensure_user_can_moderate_packages(agent)
    return ModeratorNote.objects.create(
        package_listing=listing,
        author=agent,
        content=content,
    )


@transaction.atomic
def create_version_moderator_note(
    *,
    agent: UserType,
    listing: PackageListing,
    version: PackageVersion,
    content: str,
) -> ModeratorNote:
    listing.community.ensure_user_can_moderate_packages(agent)
    if version.package_id != listing.package_id:
        raise ValidationError("The version does not belong to the listing's package.")
    return ModeratorNote.objects.create(
        package_listing=listing,
        package_version=version,
        author=agent,
        content=content,
    )


@transaction.atomic
def update_moderator_note(
    *,
    agent: UserType,
    note: ModeratorNote,
    content: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> ModeratorNote:
    # Notes are independent (no single-active slot), so toggling one never
    # affects the others.
    note.relevant_community.ensure_user_can_moderate_packages(agent)

    update_fields = []
    if content is not None:
        note.content = content
        update_fields.append("content")
    if is_active is not None:
        note.is_active = is_active
        update_fields.append("is_active")

    if update_fields:
        note.save(update_fields=update_fields)
    return note


@transaction.atomic
def delete_moderator_note(*, agent: UserType, note: ModeratorNote) -> None:
    note.relevant_community.ensure_user_can_moderate_packages(agent)
    note.delete()
