
from enum import Enum


class KafkaTopics(str, Enum):
    METRICS_ACCOUNTS = "ts.metrics.accounts"
    METRICS_MODERATION = "ts.metrics.moderation"
    METRICS_PACKAGES = "ts.metrics.packages"
    METRICS_SUBMISSIONS = "ts.metrics.submissions"


class AccountEvents(str, Enum):
    USER_CREATED = "user.created"


class ModerationEvents(str, Enum):
    LISTING_APPROVED = "listing.approved"
    LISTING_REPORTED = "listing.reported"


class PackageEvents(str, Enum):
    PACKAGE_DEPRECATED = "package.deprecated"
    PACKAGE_UNDEPRECATED = "package.undeprecated"


class SubmissionEvents(str, Enum):
    SUBMISSION_SUCCESS = "submission.success"
    # TODO: Submission failure
