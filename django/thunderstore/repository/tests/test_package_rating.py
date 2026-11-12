import json
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from rest_framework.exceptions import PermissionDenied

from thunderstore.account.models import ServiceAccount
from thunderstore.core.types import UserType
from thunderstore.repository.models import Package
from thunderstore.repository.models.package_rating import PackageRating
from thunderstore.ts_analytics.kafka import KafkaTopic

SEND_KAFKA_MESSAGE = "thunderstore.repository.tasks.likes.send_kafka_message"


@pytest.fixture
def mock_send_kafka_message():
    with patch(SEND_KAFKA_MESSAGE) as mock:
        yield mock


@pytest.mark.django_db
def test_package_rating__success(user: UserType, package: Package) -> None:
    assert len(PackageRating.objects.filter(rater=user, package=package)) == 0
    assert package.rating_score == 0

    # First run should add a rating
    result_state = PackageRating.rate_package(user, package, "rated")
    package = Package.objects.get(pk=package.pk)
    assert len(PackageRating.objects.filter(rater=user, package=package)) == 1
    assert result_state == "rated"
    assert package.rating_score == 1

    # Second run should be no-op
    result_state = PackageRating.rate_package(user, package, "rated")
    package = Package.objects.get(pk=package.pk)
    assert len(PackageRating.objects.filter(rater=user, package=package)) == 1
    assert result_state == "rated"
    assert package.rating_score == 1

    # First run should remove
    result_state = PackageRating.rate_package(user, package, "unrated")
    package = Package.objects.get(pk=package.pk)
    assert len(PackageRating.objects.filter(rater=user, package=package)) == 0
    assert result_state == "unrated"
    assert package.rating_score == 0

    # Second run should be no-op
    result_state = PackageRating.rate_package(user, package, "unrated")
    package = Package.objects.get(pk=package.pk)
    assert len(PackageRating.objects.filter(rater=user, package=package)) == 0
    assert result_state == "unrated"
    assert package.rating_score == 0


@pytest.mark.django_db
def test_package_rating__like_sends_one_kafka_event(
    user: UserType,
    package: Package,
    mock_send_kafka_message,
    django_capture_on_commit_callbacks,
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        PackageRating.rate_package(user, package, "rated")
        PackageRating.rate_package(user, package, "rated")

    mock_send_kafka_message.assert_called_once()
    kwargs = mock_send_kafka_message.call_args.kwargs
    payload = json.loads(kwargs["payload_string"])
    assert kwargs["topic"] == KafkaTopic.A_PACKAGE_LIKE_V1
    assert payload["package_id"] == package.pk
    assert payload["action"] == "like"


@pytest.mark.django_db
def test_package_rating__unlike_sends_one_kafka_event(
    user: UserType,
    package: Package,
    mock_send_kafka_message,
    django_capture_on_commit_callbacks,
) -> None:
    PackageRating.objects.create(rater=user, package=package)

    with django_capture_on_commit_callbacks(execute=True):
        PackageRating.rate_package(user, package, "unrated")
        PackageRating.rate_package(user, package, "unrated")

    mock_send_kafka_message.assert_called_once()
    kwargs = mock_send_kafka_message.call_args.kwargs
    payload = json.loads(kwargs["payload_string"])
    assert kwargs["topic"] == KafkaTopic.A_PACKAGE_LIKE_V1
    assert payload["package_id"] == package.pk
    assert payload["action"] == "unlike"


@pytest.mark.django_db
def test_package_rating__fail_bad_target(user: UserType, package: Package) -> None:
    with pytest.raises(ValidationError, match="Invalid target_state"):
        PackageRating.rate_package(user, package, "bad")  # noqa


@pytest.mark.django_db
def test_package_rating__fail_no_user(
    package: Package,
) -> None:
    with pytest.raises(PermissionDenied, match="Must be authenticated"):
        PackageRating.rate_package(None, package, "rated")


@pytest.mark.django_db
def test_package_rating__fail_user_inactive(user: UserType, package: Package) -> None:
    user.is_active = False
    user.save()

    with pytest.raises(PermissionDenied, match="User has been deactivated"):
        PackageRating.rate_package(user, package, "rated")


@pytest.mark.django_db
def test_package_rating__fail_user_serviceaccount(
    service_account: ServiceAccount, package: Package
) -> None:
    with pytest.raises(
        PermissionDenied, match="Service accounts are unable to perform this action"
    ):
        PackageRating.rate_package(service_account.user, package, "rated")
