import pytest


@pytest.mark.django_db
def test_api_experimental_communities_list(
    api_client,
):
    response = api_client.get(
        "/api/experimental/community/",
        HTTP_ACCEPT="application/json",
    )
    assert response.status_code == 200
    assert isinstance(response.json()["results"], list)
