from thunderstore.core.utils import ChoiceEnum


class PackageListingReviewStatus(ChoiceEnum):
    unreviewed = "unreviewed"
    approved = "approved"
    rejected = "rejected"


class ModeratorNoteTargetType(ChoiceEnum):
    """
    What a public ModeratorNote is attached to.

    The value is derived from which foreign keys are populated (see
    ``ModeratorNote.target_type``); it is not a stored column.
    """

    community = "community"
    listing = "listing"
    version = "version"
