from django.apps import AppConfig
from django.db.models.signals import post_save


class AnalyticsAppConfig(AppConfig):
    name = "thunderstore.ts_analytics"
    label = "ts_analytics"

    def ready(self):
        from thunderstore.community.models import Community, PackageListing
        from thunderstore.repository.models import Package, PackageVersion
        from thunderstore.ts_analytics.signals import (
            community_post_save,
            package_listing_post_save,
            package_post_save,
            package_version_post_save,
        )

        post_save.connect(
            receiver=package_post_save,
            sender=Package,
            dispatch_uid="analytics_package_post_save",
        )
        post_save.connect(
            receiver=package_version_post_save,
            sender=PackageVersion,
            dispatch_uid="analytics_package_version_post_save",
        )
        post_save.connect(
            receiver=package_listing_post_save,
            sender=PackageListing,
            dispatch_uid="analytics_package_listing_post_save",
        )
        post_save.connect(
            receiver=community_post_save,
            sender=Community,
            dispatch_uid="analytics_community_post_save",
        )
