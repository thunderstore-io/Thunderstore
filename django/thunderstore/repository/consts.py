import re
from dataclasses import dataclass

from django.db import models

from thunderstore.core.utils import ChoiceEnum

PACKAGE_NAME_REGEX = re.compile(r"^[a-zA-Z0-9\_]+$")
PACKAGE_VERSION_REGEX = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


PACKAGE_REFERENCE_COMPONENT_REGEX = re.compile(
    r"^[a-zA-Z0-9]+([a-zA-Z0-9\_]+[a-zA-Z0-9])?$"
)


class PackageVersionReviewStatus(ChoiceEnum):
    unreviewed = "unreviewed"
    approved = "approved"
    rejected = "rejected"


class MarkdownDocument(models.TextChoices):
    README = "readme", "README"
    CHANGELOG = "changelog", "CHANGELOG"


@dataclass(frozen=True)
class MarkdownFields:
    original: str
    override: str
    edited_at: str
    edited_by: str
    filename: str


MARKDOWN_FIELDS = {
    MarkdownDocument.README: MarkdownFields(
        original="readme",
        override="readme_override",
        edited_at="readme_override_edited_at",
        edited_by="readme_override_edited_by",
        filename="README.md",
    ),
    MarkdownDocument.CHANGELOG: MarkdownFields(
        original="changelog",
        override="changelog_override",
        edited_at="changelog_override_edited_at",
        edited_by="changelog_override_edited_by",
        filename="CHANGELOG.md",
    ),
}
