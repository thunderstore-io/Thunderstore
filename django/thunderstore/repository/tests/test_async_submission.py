from typing import Any, Dict

import pytest

from thunderstore.community.factories import CommunityFactory, PackageCategoryFactory
from thunderstore.community.models import Community
from thunderstore.core.types import UserType
from thunderstore.repository.models import (
    AsyncPackageSubmission,
    PackageSubmissionStatus,
    Team,
    TeamMember,
    TeamMemberRole,
)


@pytest.mark.django_db(transaction=True)
def test_async_package_submission_flow(
    user: UserType,
    manifest_v1_data: Dict[str, Any],
    team: Team,
    community: Community,
    manifest_v1_package_upload_id: str,
):
    com2 = CommunityFactory()
    com3 = CommunityFactory()
    com2_cat1 = PackageCategoryFactory(community=com2)
    com3_cat1 = PackageCategoryFactory(community=com3)
    com3_cat2 = PackageCategoryFactory(community=com3)

    TeamMember.objects.create(
        user=user,
        team=team,
        role=TeamMemberRole.owner,
    )

    submission: AsyncPackageSubmission = AsyncPackageSubmission.objects.create(
        owner=user,
        file_id=manifest_v1_package_upload_id,
        form_data={
            "author_name": team.name,
            "community_categories": {
                com2.identifier: [com2_cat1.slug],
                com3.identifier: [com3_cat1.slug, com3_cat2.slug],
            },
            "communities": [
                community.identifier,
                com2.identifier,
                com3.identifier,
            ],
            "has_nsfw_content": True,
        },
    )
    assert submission.status == PackageSubmissionStatus.PENDING
    assert submission.datetime_scheduled is None
    submission.schedule_if_appropriate()
    submission.refresh_from_db()
    assert submission.datetime_scheduled is not None
    assert submission.status == PackageSubmissionStatus.FINISHED

    assert submission.form_errors is None
    assert submission.task_error is None
    assert submission.created_version is not None
    assert submission.created_version.package.namespace.name == team.name
    assert submission.created_version.name == manifest_v1_data["name"]
    assert (
        submission.created_version.version_number == manifest_v1_data["version_number"]
    )
