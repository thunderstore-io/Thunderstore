from thunderstore.core.utils import ChoiceEnum


class PackageListingReviewStatus(ChoiceEnum):
    unreviewed = "unreviewed"
    approved = "approved"
    rejected = "rejected"


AI_GENERATED_CATEGORY_SLUG = "ai-generated"
AI_GENERATED_CATEGORY_NAME = "AI Generated"
