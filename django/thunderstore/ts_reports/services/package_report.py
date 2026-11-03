from django.db import transaction

from thunderstore.core.types import UserType
from thunderstore.permissions.utils import validate_user
from thunderstore.repository.models import Package, PackageListing, PackageVersion
from thunderstore.ts_reports.models import PackageReport


@transaction.atomic
def report_package_listing(
    agent: UserType,
    reason: str,
    package: Package,
    package_listing: PackageListing,
    package_version: PackageVersion,
    description: str,
) -> None:
    user = validate_user(agent)

    PackageReport.handle_user_report(
        reason=reason,
        submitted_by=user,
        package=package,
        package_listing=package_listing,
        package_version=package_version,
        description=description,
    )
