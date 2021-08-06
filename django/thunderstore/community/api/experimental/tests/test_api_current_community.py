import pytest

from thunderstore.community.api.experimental.serializers import CommunitySerializer


@pytest.mark.django_db
def test_api_experimental_current_community(user, api_client, community):
    api_client.force_authenticate(user)
    response = api_client.get(
        "/api/experimental/current-community/",
        HTTP_ACCEPT="application/json",
    )
    assert response.status_code == 200
    assert response.json() == CommunitySerializer(community).data
