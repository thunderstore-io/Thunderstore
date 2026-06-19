from typing import TYPE_CHECKING, Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from thunderstore.community.consts import ModeratorNoteTargetType
from thunderstore.core.mixins import AdminLinkMixin, TimestampMixin

if TYPE_CHECKING:
    from thunderstore.community.models import Community

__all__ = ["ModeratorNote"]


class ModeratorNote(TimestampMixin, AdminLinkMixin):
    """
    A public, moderator-authored note/disclaimer.

    A note targets exactly one of:
      * a whole community (``community`` set),
      * a package's listing in a community (``package_listing`` set), or
      * a specific version of a package in a community
        (``package_listing`` **and** ``package_version`` both set).

    Version notes intentionally carry ``package_listing`` as well as
    ``package_version`` so that moderator authority and visibility stay
    scoped to a single community: the same ``PackageVersion`` may be listed
    in several communities, and a moderator of one community must not be able
    to post a note that surfaces in another.

    The content is always public; there is no private/internal variant here
    (the moderator-internal ``PackageListing.notes`` field is unrelated).
    """

    community = models.ForeignKey(
        "community.Community",
        related_name="moderator_notes",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    package_listing = models.ForeignKey(
        "community.PackageListing",
        related_name="moderator_notes",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    package_version = models.ForeignKey(
        "repository.PackageVersion",
        related_name="moderator_notes",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="authored_moderator_notes",
        # Notes survive their author's account deletion; authorship is kept
        # for audit purposes but is never exposed publicly.
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    content = models.TextField()
    # Notes can be turned off without deleting them (kept for audit). Multiple
    # notes may be active on the same resource at once; all active ones are shown.
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("-datetime_created",)
        constraints = [
            models.CheckConstraint(
                name="moderator_note_valid_target",
                check=(
                    # Community note.
                    Q(
                        community__isnull=False,
                        package_listing__isnull=True,
                        package_version__isnull=True,
                    )
                    # Listing note.
                    | Q(
                        community__isnull=True,
                        package_listing__isnull=False,
                        package_version__isnull=True,
                    )
                    # Version note (scoped to a listing's community).
                    | Q(
                        community__isnull=True,
                        package_listing__isnull=False,
                        package_version__isnull=False,
                    )
                ),
            ),
        ]

    def __str__(self) -> str:
        return f"Moderator note ({self.target_type}) #{self.pk}"

    def validate(self) -> None:
        targets_set = sum(
            (
                self.community_id is not None,
                self.package_listing_id is not None,
            )
        )
        if targets_set != 1:
            raise ValidationError(
                "A moderator note must target exactly one of a community or a "
                "package listing."
            )
        if self.package_version_id is not None:
            if self.package_listing_id is None:
                raise ValidationError(
                    "A version note must also reference its package listing."
                )
            if self.package_version.package_id != self.package_listing.package_id:
                raise ValidationError(
                    "package_version and package_listing must belong to the same "
                    "package."
                )

    def save(self, *args, **kwargs):
        self.validate()
        return super().save(*args, **kwargs)

    @property
    def target_type(self) -> str:
        if self.community_id is not None:
            return ModeratorNoteTargetType.community
        if self.package_version_id is not None:
            return ModeratorNoteTargetType.version
        return ModeratorNoteTargetType.listing

    @property
    def relevant_community(self) -> Optional["Community"]:
        """The community whose moderators are allowed to manage this note."""
        if self.community_id is not None:
            return self.community
        if self.package_listing_id is not None:
            return self.package_listing.community
        return None

    @property
    def version_number(self) -> Optional[str]:
        if self.package_version_id is not None:
            return self.package_version.version_number
        return None
