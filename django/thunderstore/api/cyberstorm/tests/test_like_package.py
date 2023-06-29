import json
from typing import Any, Dict, Optional

import pytest
from django.contrib.sessions.backends.db import SessionStore
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from thunderstore.community.factories import CommunitySiteFactory, PackageListingFactory
from thunderstore.core.types import UserType
from thunderstore.repository.factories import PackageRatingFactory
from thunderstore.repository.models.package_rating import PackageRating


@pytest.mark.django_db
def test_api_cyberstorm_package_like(api_client: APIClient, user: UserType) -> None:

    session_key = _create_session(user)

    site1 = CommunitySiteFactory()
    listing1 = PackageListingFactory(community_=site1.community)
    assert len(PackageRating.objects.filter(rater=user, package=listing1.package)) == 0
    data = __query_api(
        api_client,
        listing1.package.uuid4,
        {"target_state": "rated"},
        session_key,
    )
    assert data["state"] == "rated"
    assert data["score"] == 1
    assert len(PackageRating.objects.filter(rater=user, package=listing1.package)) == 1

    data = __query_api(
        api_client,
        listing1.package.uuid4,
        {"target_state": "unrated"},
        session_key,
    )
    assert data["state"] == "unrated"
    assert data["score"] == 0
    assert len(PackageRating.objects.filter(rater=user, package=listing1.package)) == 0


@pytest.mark.django_db
@override_settings(SESSION_COOKIE_AGE=0)
def test_api_cyberstorm_package_like_session_expired_rate_change_rated_fails(
    api_client: APIClient, user: UserType
) -> None:

    session_key = _create_session(user)

    site1 = CommunitySiteFactory()
    listing1 = PackageListingFactory(community_=site1.community)
    assert len(PackageRating.objects.filter(rater=user, package=listing1.package)) == 0
    data = __query_api(
        api_client,
        listing1.package.uuid4,
        {"target_state": "rated"},
        session_key,
        response_status_code=401,
    )
    assert len(PackageRating.objects.filter(rater=user, package=listing1.package)) == 0
    assert data["detail"] == "Invalid token."


@pytest.mark.django_db
def test_api_cyberstorm_package_like_no_session_rate_change_rated_fails(
    api_client: APIClient, user: UserType
) -> None:

    site1 = CommunitySiteFactory()
    listing1 = PackageListingFactory(community_=site1.community)
    assert len(PackageRating.objects.filter(rater=user, package=listing1.package)) == 0
    data = __query_api(
        api_client,
        listing1.package.uuid4,
        {"target_state": "rated"},
        response_status_code=401,
    )
    assert len(PackageRating.objects.filter(rater=user, package=listing1.package)) == 0
    assert data["detail"] == "Authentication credentials were not provided."


@pytest.mark.django_db
def test_api_cyberstorm_package_like_bad_session_rate_change_rated_fails(
    api_client: APIClient, user: UserType
) -> None:

    site1 = CommunitySiteFactory()
    listing1 = PackageListingFactory(community_=site1.community)
    assert len(PackageRating.objects.filter(rater=user, package=listing1.package)) == 0
    data = __query_api(
        api_client,
        listing1.package.uuid4,
        {"target_state": "rated"},
        "potato",
        response_status_code=401,
    )
    assert len(PackageRating.objects.filter(rater=user, package=listing1.package)) == 0
    assert data["detail"] == "Invalid token."


@pytest.mark.django_db
@override_settings(SESSION_COOKIE_AGE=0)
def test_api_cyberstorm_package_like_session_expired_rate_change_unrated_fails(
    api_client: APIClient, user: UserType
) -> None:

    session_key = _create_session(user)

    site1 = CommunitySiteFactory()
    listing1 = PackageListingFactory(community_=site1.community)
    PackageRatingFactory(package=listing1.package, rater=user)
    assert len(PackageRating.objects.filter(rater=user, package=listing1.package)) == 1
    data = __query_api(
        api_client,
        listing1.package.uuid4,
        {"target_state": "unrated"},
        session_key,
        response_status_code=401,
    )
    assert len(PackageRating.objects.filter(rater=user, package=listing1.package)) == 1
    assert data["detail"] == "Invalid token."


@pytest.mark.django_db
def test_api_cyberstorm_package_like_no_session_rate_change_unrated_fails(
    api_client: APIClient, user: UserType
) -> None:

    site1 = CommunitySiteFactory()
    listing1 = PackageListingFactory(community_=site1.community)
    PackageRatingFactory(package=listing1.package, rater=user)
    assert len(PackageRating.objects.filter(rater=user, package=listing1.package)) == 1
    data = __query_api(
        api_client,
        listing1.package.uuid4,
        {"target_state": "unrated"},
        response_status_code=401,
    )
    assert len(PackageRating.objects.filter(rater=user, package=listing1.package)) == 1
    assert data["detail"] == "Authentication credentials were not provided."


@pytest.mark.django_db
def test_api_cyberstorm_package_like_bad_session_rate_change_unrated_fails(
    api_client: APIClient, user: UserType
) -> None:

    site1 = CommunitySiteFactory()
    listing1 = PackageListingFactory(community_=site1.community)
    PackageRatingFactory(package=listing1.package, rater=user)
    assert len(PackageRating.objects.filter(rater=user, package=listing1.package)) == 1
    data = __query_api(
        api_client,
        listing1.package.uuid4,
        {"target_state": "unrated"},
        "potato",
        response_status_code=401,
    )
    assert len(PackageRating.objects.filter(rater=user, package=listing1.package)) == 1
    assert data["detail"] == "Invalid token."


def __query_api(
    client: APIClient,
    uuid4: str,
    payload: Dict,
    session_key: Optional[str] = None,
    response_status_code=200,
) -> Dict:
    url = reverse(
        "api:cyberstorm:cyberstorm.like_package",
        kwargs={
            "uuid4": uuid4,
        },
    )
    kwargs: Dict[str, Any] = {"content_type": "application/json"}

    if session_key:
        kwargs["HTTP_AUTHORIZATION"] = f"Session {session_key}"
    response = client.post(f"{url}", data=str(json.dumps(payload)), **kwargs)
    assert response.status_code == response_status_code
    return response.json()


def _create_session(user: UserType) -> str:
    store = SessionStore()
    store.create()
    store["_auth_user_id"] = user.pk
    store.save()
    return store.session_key
