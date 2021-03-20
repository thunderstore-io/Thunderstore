import pytest

from thunderstore.community.models import Community


@pytest.mark.django_db
def test_api_experimental_categories_list(
    api_client,
    community,
):
    response = api_client.get(
        f"/api/experimental/community/{community.identifier}/category/",
        HTTP_ACCEPT="application/json",
    )
    assert response.status_code == 200
    assert isinstance(response.json()["packageCategories"], list)


@pytest.mark.django_db
def test_api_experimental_categories_list_not_found(
    api_client,
):
    invalid_community_identifier = "NOT_A_COMMUNITY_IDENTIFIER"
    assert not Community.objects.filter(
        identifier=invalid_community_identifier,
    ).exists()
    response = api_client.get(
        f"/api/experimental/community/{invalid_community_identifier}/category/",
        HTTP_ACCEPT="application/json",
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Not found."}
