from io import StringIO

import pytest
from django.core.management import call_command


@pytest.mark.django_db
def test_management_command_default_args(mocker):
    mock_cleanup = mocker.patch(
        "thunderstore.core.management.commands.cleanup_sessions.cleanup_expired_sessions",
        return_value=42,
    )
    out = StringIO()
    call_command("cleanup_sessions", stdout=out)

    mock_cleanup.assert_called_once_with(batch_size=10000, sleep_time=0.1)
    output = out.getvalue()
    assert "Starting session cleanup" in output
    assert "Deleted 42 expired sessions" in output


@pytest.mark.django_db
def test_management_command_custom_args(mocker):
    mock_cleanup = mocker.patch(
        "thunderstore.core.management.commands.cleanup_sessions.cleanup_expired_sessions",
        return_value=7,
    )
    out = StringIO()
    call_command("cleanup_sessions", "--batch-size=500", "--sleep=0.5", stdout=out)

    mock_cleanup.assert_called_once_with(batch_size=500, sleep_time=0.5)
    output = out.getvalue()
    assert "Deleted 7 expired sessions" in output
