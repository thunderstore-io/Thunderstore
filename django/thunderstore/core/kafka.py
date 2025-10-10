from enum import Enum


class KafkaTopics(str, Enum):
    METRICS_PACKAGES = "ts.metrics.packages"

class PackageEvents(str, Enum):
    PACKAGE_DOWNLOADED = "package.downloaded"
