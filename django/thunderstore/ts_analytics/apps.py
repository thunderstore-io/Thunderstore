from django.apps import AppConfig
from django.db.models.signals import post_save


class AnalyticsAppConfig(AppConfig):
    name = "thunderstore.ts_analytics"
    label = "ts_analytics"

    def ready(self):
        # Connect the signal handlers
        from thunderstore.community.models import Community, PackageListing
        from thunderstore.metrics.models import PackageVersionDownloadEvent
        from thunderstore.repository.models import Package, PackageVersion
        from thunderstore.ts_analytics.signals import (
            community_post_save,
            package_listing_post_save,
            package_post_save,
            package_version_download_event_post_save,
            package_version_post_save,
        )

        post_save.connect(
            package_version_download_event_post_save, sender=PackageVersionDownloadEvent
        )
        post_save.connect(package_post_save, sender=Package)
        post_save.connect(package_version_post_save, sender=PackageVersion)
        post_save.connect(package_listing_post_save, sender=PackageListing)
        post_save.connect(community_post_save, sender=Community)
