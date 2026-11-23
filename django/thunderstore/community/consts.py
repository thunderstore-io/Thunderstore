from thunderstore.core.utils import ChoiceEnum

DEFAULT_COMMUNITY_IDENTIFIER = "riskofrain2"


class PackageListingReviewStatus(ChoiceEnum):
    unreviewed = "unreviewed"
    approved = "approved"
    rejected = "rejected"
