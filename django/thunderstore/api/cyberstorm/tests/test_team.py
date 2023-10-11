import pytest
from rest_framework.test import APIClient

from thunderstore.community.models import CommunitySite
from thunderstore.repository.models.team import Team, TeamMember


@pytest.mark.django_db
def test_api_cyberstorm_team_detail_success(
    client: APIClient,
    community_site: CommunitySite,
    team: Team,
    team_member: TeamMember,
):
    response = client.get(
        f"/api/cyberstorm/team/{team.name}/",
        HTTP_HOST=community_site.site.domain,
    )
    result = response.json()
    assert response.status_code == 200
    assert team.name == result["name"]
    assert team.donation_link == result["donation_link"]

    members = team.members.all()
    assert len(members) == 1
    assert len(members) == len(result["members"])

    member = members.first()
    assert result["members"][0]["role"] == member.role
    assert result["members"][0]["user"]["identifier"] == str(member.user.pk)
    assert result["members"][0]["user"]["username"] == member.user.username


@pytest.mark.django_db
def test_api_cyberstorm_team_detail_failure(
    client: APIClient, community_site: CommunitySite
):
    response = client.get(
        f"/api/cyberstorm/team/bad/",
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 404
