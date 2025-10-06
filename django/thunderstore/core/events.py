from enum import Enum


class KafkaTopics(str, Enum):
    METRICS_ACCOUNTS = "ts.metrics.accounts"
    METRICS_MODERATION = "ts.metrics.moderation"
    METRICS_SUBMISSIONS = "ts.metrics.submissions"
    METRICS_TEAMS = "ts.metrics.teams"


class AccountEvents(str, Enum):
    USER_CREATED = "user.created"


class ModerationEvents(str, Enum):
    LISTING_APPROVED = "listing.approved"


class SubmissionEvents(str, Enum):
    SUBMISSION_SUCCESS = "submission.success"


class TeamEvents(str, Enum):
    TEAM_CREATED = "team.created"
