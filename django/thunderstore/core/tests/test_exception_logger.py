import pytest

from thunderstore.core.utils import ExceptionLogger


@pytest.mark.django_db
def test_exception_logger_continues(settings, mocker):
    mocked = mocker.patch("thunderstore.core.utils.capture_exception")
    settings.ALWAYS_RAISE_EXCEPTIONS = False
    exception = AssertionError("Test")

    with ExceptionLogger(continue_on_error=True):
        raise exception

    assert mocked.called_once_with(exception)


@pytest.mark.django_db
def test_exception_logger_raises(settings, mocker):
    mocked = mocker.patch("thunderstore.core.utils.capture_exception")
    settings.ALWAYS_RAISE_EXCEPTIONS = False
    exception = AssertionError("Test")

    with pytest.raises(AssertionError, match="Test"):
        with ExceptionLogger(continue_on_error=False):
            raise exception

    assert mocked.called_once_with(exception)
