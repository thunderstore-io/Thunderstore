from thunderstore.core.utils import ChoiceEnum


class PackageListingReviewStatus(ChoiceEnum):
    unreviewed = "unreviewed"
    approved = "approved"
    rejected = "rejected"
