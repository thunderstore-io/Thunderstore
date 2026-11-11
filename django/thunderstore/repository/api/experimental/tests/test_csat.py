import json
import uuid
from datetime import datetime
from typing import Any, Dict
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.test import APIClient

from thunderstore.ts_analytics.kafka import KafkaTopic

VIEWS_MODULE = "thunderstore.repository.api.experimental.views.csat"

VALID_SUBMISSION = {
    "score": 4,
    "comment": "Profiles are great, updates are slow. I see it in my sleep.",
    "install_id": "3f2c9a8e-6d41-4c2b-9f0e-1a7b5c3d2e10",
    "app_version": "1.126.0",
}


def submission(**overrides: Any) -> Dict[str, Any]:
    return {**VALID_SUBMISSION, **overrides}


def submission_without(field: str) -> Dict[str, Any]:
    return {k: v for k, v in VALID_SUBMISSION.items() if k != field}


def get_status(
    client: APIClient,
    install_id: str = VALID_SUBMISSION["install_id"],
) -> Response:
    return client.get(
        reverse("api:experimental:csat.status"),
        data={"install_id": install_id},
    )


def submit(client: APIClient, data: Dict[str, Any]) -> Response:
    return client.post(
        reverse("api:experimental:csat.submit"),
        data=data,
        format="json",
    )


@pytest.fixture
def csat_enabled(settings) -> None:
    settings.CSAT_SURVEY_ENABLED = True
    settings.CSAT_SURVEY_ELIGIBLE_CHANCE = 1.0


@pytest.fixture
def mock_send_kafka_message():
    with patch(f"{VIEWS_MODULE}.send_kafka_message") as mock:
        yield mock


@pytest.mark.django_db
def test_experimental_api_csat_status_requires_install_id(
    api_client: APIClient,
    csat_enabled,
) -> None:
    missing = api_client.get(reverse("api:experimental:csat.status"))
    assert missing.status_code == 400
    assert "install_id" in missing.json()

    invalid = get_status(api_client, install_id="not-a-uuid")
    assert invalid.status_code == 400
    assert "install_id" in invalid.json()


@pytest.mark.django_db
def test_experimental_api_csat_status_disabled(
    api_client: APIClient,
    settings,
) -> None:
    settings.CSAT_SURVEY_ENABLED = False
    disabled = {"enabled": False, "eligible": False}

    response = get_status(api_client)
    assert response.status_code == 200
    assert response.json() == disabled

    missing = api_client.get(reverse("api:experimental:csat.status"))
    assert missing.status_code == 200
    assert missing.json() == disabled

    invalid = get_status(api_client, install_id="not-a-uuid")
    assert invalid.status_code == 200
    assert invalid.json() == disabled


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("roll", "chance", "eligible"),
    (
        (0.0, 0.0, False),
        (0.49, 0.5, True),
        (0.5, 0.5, False),
        (0.999, 1.0, True),
    ),
)
def test_experimental_api_csat_status_rolls_eligibility(
    api_client: APIClient,
    settings,
    roll: float,
    chance: float,
    eligible: bool,
) -> None:
    settings.CSAT_SURVEY_ENABLED = True
    settings.CSAT_SURVEY_ELIGIBLE_CHANCE = chance
    with patch(f"{VIEWS_MODULE}.random", return_value=roll):
        response = get_status(api_client)
    assert response.status_code == 200
    assert response.json() == {"enabled": True, "eligible": eligible}


@pytest.mark.django_db
def test_experimental_api_csat_status_is_never_cached(
    api_client: APIClient,
    csat_enabled,
) -> None:
    response = get_status(api_client)
    assert "no-store" in response["Cache-Control"]


@pytest.mark.django_db
def test_experimental_api_csat_ignores_invalid_session(
    api_client: APIClient,
    csat_enabled,
    mock_send_kafka_message,
) -> None:
    api_client.credentials(HTTP_AUTHORIZATION="Session invalid-session-key")
    assert get_status(api_client).status_code == 200
    assert submit(api_client, VALID_SUBMISSION).status_code == 200


@pytest.mark.django_db
def test_experimental_api_csat_submit_disabled(
    api_client: APIClient,
    settings,
    mock_send_kafka_message,
) -> None:
    settings.CSAT_SURVEY_ENABLED = False
    response = submit(api_client, VALID_SUBMISSION)
    assert response.status_code == 503
    mock_send_kafka_message.delay.assert_not_called()


@pytest.mark.django_db
def test_experimental_api_csat_submit_sends_kafka_event(
    api_client: APIClient,
    csat_enabled,
    mock_send_kafka_message,
) -> None:
    before = timezone.now()
    response = submit(api_client, VALID_SUBMISSION)
    after = timezone.now()

    assert response.status_code == 200
    assert response.json() == {}

    mock_send_kafka_message.delay.assert_called_once()
    call_kwargs = mock_send_kafka_message.delay.call_args.kwargs
    assert call_kwargs["topic"] == KafkaTopic.A_CSAT_SURVEY_RESPONSE_V1

    payload = json.loads(call_kwargs["payload_string"])
    assert set(payload) == {
        "id",
        "timestamp",
        "score",
        "comment",
        "install_id",
        "app_version",
    }
    uuid.UUID(payload["id"])
    assert before <= datetime.fromisoformat(payload["timestamp"]) <= after
    assert payload["score"] == VALID_SUBMISSION["score"]
    assert payload["comment"] == VALID_SUBMISSION["comment"]
    assert payload["install_id"] == VALID_SUBMISSION["install_id"]
    assert payload["app_version"] == VALID_SUBMISSION["app_version"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "data",
    (
        pytest.param(submission_without("comment"), id="missing"),
        pytest.param(submission(comment=None), id="null"),
        pytest.param(submission(comment=""), id="empty"),
        pytest.param(submission(comment="   "), id="whitespace"),
    ),
)
def test_experimental_api_csat_submit_stores_absent_comment_as_empty(
    api_client: APIClient,
    csat_enabled,
    mock_send_kafka_message,
    data: Dict[str, Any],
) -> None:
    response = submit(api_client, data)
    assert response.status_code == 200
    payload_string = mock_send_kafka_message.delay.call_args.kwargs["payload_string"]
    assert json.loads(payload_string)["comment"] == ""


@pytest.mark.django_db
@pytest.mark.parametrize(
    "data",
    (
        pytest.param(submission(score=1), id="score-min"),
        pytest.param(submission(score=5), id="score-max"),
        pytest.param(submission(comment="a" * 5000), id="comment-max-length"),
        pytest.param(submission(app_version="1" * 64), id="app-version-max-length"),
    ),
)
def test_experimental_api_csat_submit_accepts_boundary_values(
    api_client: APIClient,
    csat_enabled,
    mock_send_kafka_message,
    data: Dict[str, Any],
) -> None:
    response = submit(api_client, data)
    assert response.status_code == 200
    mock_send_kafka_message.delay.assert_called_once()


@pytest.mark.django_db
def test_experimental_api_csat_submit_ignores_unknown_fields(
    api_client: APIClient,
    csat_enabled,
    mock_send_kafka_message,
) -> None:
    response = submit(api_client, submission(platform="windows"))
    assert response.status_code == 200
    payload_string = mock_send_kafka_message.delay.call_args.kwargs["payload_string"]
    assert "platform" not in json.loads(payload_string)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("data", "field"),
    (
        pytest.param(submission(score=0), "score", id="score-below-min"),
        pytest.param(submission(score=6), "score", id="score-above-max"),
        pytest.param(submission(score="great"), "score", id="score-not-integer"),
        pytest.param(submission_without("score"), "score", id="score-missing"),
        pytest.param(submission(comment="a" * 5001), "comment", id="comment-too-long"),
        pytest.param(
            submission(install_id="not-a-uuid"), "install_id", id="install-id-invalid"
        ),
        pytest.param(submission(install_id=None), "install_id", id="install-id-null"),
        pytest.param(
            submission_without("install_id"), "install_id", id="install-id-missing"
        ),
        pytest.param(
            submission(app_version="1" * 65),
            "app_version",
            id="app-version-too-long",
        ),
        pytest.param(
            submission_without("app_version"),
            "app_version",
            id="app-version-missing",
        ),
    ),
)
def test_experimental_api_csat_submit_rejects_invalid_data(
    api_client: APIClient,
    csat_enabled,
    mock_send_kafka_message,
    data: Dict[str, Any],
    field: str,
) -> None:
    response = submit(api_client, data)
    assert response.status_code == 400
    assert field in response.json()
    mock_send_kafka_message.delay.assert_not_called()
