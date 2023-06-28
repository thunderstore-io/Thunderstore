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
    resp_com = response.json()
    assert response.status_code == 200
    assert team.name == resp_com["name"]
    assert team.donation_link == resp_com["donation_link"]
    for member in resp_com["members"]:
        assert member in [
            {"username": tm.user.username, "role": tm.role} for tm in team.members.all()
        ]


@pytest.mark.django_db
def test_api_cyberstorm_team_detail_failure(
    client: APIClient, community_site: CommunitySite, team: Team
):
    response = client.get(
        f"/api/cyberstorm/team/bad/",
        HTTP_HOST=community_site.site.domain,
    )
    assert response.status_code == 404
