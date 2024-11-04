import re

from thunderstore.core.utils import ChoiceEnum

PACKAGE_NAME_REGEX = re.compile(r"^[a-zA-Z0-9\_]+$")
PACKAGE_VERSION_REGEX = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")

PACKAGE_REFERENCE_COMPONENT_REGEX = re.compile(
    r"^[a-zA-Z0-9]+([a-zA-Z0-9\_]+[a-zA-Z0-9])?$"
)


class PackageVersionReviewStatus(ChoiceEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    skipped = "skipped"
    immune = "immune"
